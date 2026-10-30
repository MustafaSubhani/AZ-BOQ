"""Read one DXF into a compact dump: texts, dimensions, frames, tables, inserts and layers.

Blocks are expanded to world coordinates so title-block and schedule text placed
inside blocks is not lost. Text is decoded per run with the run's own font.
Geometry that is not a frame or a table line goes to a sidecar file, and every
entity type that is still not stored is counted, so a loss cannot be silent.
"""
import json
import math
from collections import Counter

import ezdxf
from ezdxf import path as ezpath
from ezdxf import recover
from ezdxf.math import Vec3

from .. import config, runlog
from ..text.mtext import decode_mtext, decode_text
from ..text.normalise import fold_homoglyphs
from . import layers as L

MAX_DEPTH = 4
READER_VERSION = 2
KEEP_LINE_ROLES = {"table", "frame"}
KEEP_POLY_ROLES = {"frame", "table", "wall", "partition", "column", "slab", "zone", "roof", "road", "fence", "survey",
                   "unclassified", "pipe"}
# These roles are annotation or hatch strokes. Their lines are not geometry.
SKIP_GEOM_ROLES = {"hatch", "furniture", "dimension", "text", "axis", "hidden", "architecture_background"}


def _open(path):
    try:
        return ezdxf.readfile(path)
    except ezdxf.DXFStructureError:
        doc, _aud = recover.readfile(path)
        return doc


def _style_fonts(doc) -> dict:
    fonts = {}
    for st in doc.styles:
        fonts[st.dxf.name.lower()] = st.dxf.get("font", "") or ""
    return fonts


def _pt(v) -> list:
    return [round(float(v[0]), 3), round(float(v[1]), 3)]


def mtext_bbox(insert, attach: int, width: float, h: float, n_lines: int, rot_deg: float = 0, line_spacing: float = 1.667):
    """Box of an MTEXT. attach is DXF group 71: 1 top-left … 9 bottom-right.

    A width of 0 means the text does not wrap. The box is then an estimate, and the
    third return value says so.
    """
    attach = int(attach or 1)
    n_lines = max(int(n_lines or 1), 1)
    h = float(h or 0)
    estimated = not width
    w = float(width) if width else h * 12
    total_h = h * (1 + (n_lines - 1) * line_spacing)
    col, row = (attach - 1) % 3, (attach - 1) // 3
    x0 = insert[0] - w * col / 2
    y1 = insert[1] + total_h * row / 2
    box = [x0, y1 - total_h, x0 + w, y1]
    if rot_deg:
        box = _rotate_box(box, insert, rot_deg)
    return [round(v, 3) for v in box], estimated


def _rotate_box(box, origin, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    ox, oy = origin[0], origin[1]
    xs, ys = [], []
    for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])):
        dx, dy = x - ox, y - oy
        xs.append(ox + dx * c - dy * s)
        ys.append(oy + dx * s + dy * c)
    return [min(xs), min(ys), max(xs), max(ys)]


def outlines_of(geom, tol: float) -> tuple[list, list]:
    """A simplified outer ring and its holes, in drawing units."""
    try:
        simple = geom.simplify(tol * 20, preserve_topology=True)
    except Exception:
        return [], []
    if simple.is_empty:
        return [], []
    polys = [simple] if simple.geom_type == "Polygon" else list(getattr(simple, "geoms", []) or [])
    rings, holes = [], []
    for poly in polys:
        if getattr(poly, "geom_type", "") != "Polygon" or poly.is_empty or poly.area <= 0:
            continue
        rings.append([[round(x, 1), round(y, 1)] for x, y in poly.exterior.coords])
        holes.extend([[[round(x, 1), round(y, 1)] for x, y in ring.coords] for ring in poly.interiors])
    return rings, holes


def fill_hatch_outlines(file_sha: str) -> int:
    """Write hatch outlines into an existing geometry file. Texts and areas stay as they are."""
    from functools import reduce
    from shapely.geometry import Polygon
    from .oda import dxf_path_for
    path = geom_path_for(file_sha)
    dxf = dxf_path_for(file_sha)
    if not path.exists() or not dxf.exists():
        return 0
    geom = json.loads(path.read_text(encoding="utf-8"))
    if geom.get("outlines") == "stored":
        return 0
    doc = _open(dxf)
    tol = _flat_tol(doc)
    found = {}
    spaces = [doc.modelspace(), *list(doc.blocks)]
    for space in spaces:
        try:
            entities = list(space)
        except Exception:
            continue
        for entity in entities:
            if entity.dxftype() != "HATCH":
                continue
            handle = entity.dxf.get("handle")
            if not handle or handle in found:
                continue
            try:
                paths = list(ezpath.from_hatch(entity))
            except Exception:
                continue
            rings = []
            for hatch_path in paths:
                pts = [(float(v.x), float(v.y)) for v in hatch_path.flattening(distance=tol)]
                if len(pts) < 3:
                    continue
                poly = Polygon(pts).buffer(0)
                if not poly.is_empty:
                    rings.append(poly)
            if not rings:
                continue
            try:
                shape = reduce(lambda a, b: a.symmetric_difference(b), sorted(rings, key=lambda g: -g.area))
            except Exception:
                continue
            outline, holes = outlines_of(shape, tol)
            if outline:
                found[handle] = {"outline": outline, "holes": holes}
    written = 0
    for hatch in geom.get("hatches") or []:
        row = found.get(hatch.get("handle"))
        if not row:
            continue
        hatch["outline"] = row["outline"]
        hatch["holes"] = row["holes"]
        written += 1
    geom["outlines"] = "stored"
    path.write_text(json.dumps(geom, ensure_ascii=False), encoding="utf-8")
    return written


def _flat_tol(doc) -> float:
    """About a hundred-thousandth of the drawing diagonal, in drawing units. $INSUNITS is not trusted."""
    mn, mx = doc.header.get("$EXTMIN", None), doc.header.get("$EXTMAX", None)
    if not mn or not mx:
        return 1.0
    diag = math.hypot(float(mx[0]) - float(mn[0]), float(mx[1]) - float(mn[1]))
    return max(diag * 1e-5, 1e-3)


def _shoelace(pts) -> float:
    area = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        area += x0 * y1 - x1 * y0
    return area / 2


def _metrics(e, tol):
    """Vertex list (capped), full length, and area when the path closes. Bulges are honoured."""
    try:
        path = ezpath.make_path(e)
        pts = [(float(v.x), float(v.y)) for v in path.flattening(distance=tol)]
    except Exception:
        return None
    if len(pts) < 2:
        return None
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    closed = bool(getattr(e, "closed", False))
    if not closed and len(pts) >= 3 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= tol * 2:
        closed = True
    area = abs(_shoelace(pts)) if closed and len(pts) >= 3 else None
    shown = [_pt(p) for p in (pts if len(pts) <= 80 else pts[:80])]
    return shown, round(length, 3), None if area is None else round(area, 3), len(pts), closed


class Dumper:
    def __init__(self, doc, tol: float):
        self.doc = doc
        self.tol = tol
        self.fonts = _style_fonts(doc)
        self.texts, self.dims, self.lines, self.polys, self.inserts, self.tables = [], [], [], [], [], []
        self.geom = {"lines": [], "circles": [], "arcs": [], "ellipses": [], "polys": [], "hatches": []}
        self.layer_counts = Counter()
        self.dropped = Counter()
        self.layer_state = {}
        for layer in doc.layers:
            self.layer_state[layer.dxf.name] = {"frozen": layer.is_frozen(), "off": not layer.is_on()}

    def _font(self, e) -> str:
        return self.fonts.get(str(e.dxf.get("style", "Standard")).lower(), "")

    def _drop(self, kind: str, layer: str):
        self.dropped[(kind, layer)] += 1

    def visit(self, e, layout: str, depth: int, block_path: tuple):
        t = e.dxftype()
        layer = e.dxf.get("layer", "0")
        self.layer_counts[layer] += 1
        role = L.role(layer)
        handle = e.dxf.get("handle") or (block_path[0] if block_path else "")
        base = {"handle": handle, "layer": layer, "role": role, "layout": layout}
        if block_path:
            base["block"] = list(block_path)
        if t in ("TEXT", "ATTRIB", "ATTDEF"):
            if t == "ATTDEF":
                self._drop(t, layer)
                return
            res = decode_text(e.dxf.get("text", ""), self._font(e))
            self._add_text(base, t, e.dxf.get("insert", Vec3()), e.dxf.get("height", 0), e.dxf.get("rotation", 0), res)
        elif t == "MTEXT":
            res = decode_mtext(e.text, self._font(e))
            self._add_text(base, t, e.dxf.get("insert", Vec3()), e.dxf.get("char_height", 0), e.dxf.get("rotation", 0),
                           res, e)
        elif t == "DIMENSION":
            try:
                m = e.get_measurement()
            except Exception:
                m = None
            measurement = float(m) if isinstance(m, (int, float)) else None
            override = e.dxf.get("text", "")
            p2, p3 = e.dxf.get("defpoint2", None), e.dxf.get("defpoint3", None)
            self.dims.append({**base, "measurement": measurement, "text": override,
                              "p1": _pt(p2) if p2 is not None else None, "p2": _pt(p3) if p3 is not None else None,
                              "at": _pt(e.dxf.get("text_midpoint", e.dxf.get("defpoint", Vec3())))})
        elif t == "ACAD_TABLE":
            self._table(e, base)
        elif t == "MULTILEADER":
            self._leader(e, base)
        elif t == "HATCH":
            self._hatch(e, base)
        elif t == "LINE":
            self._line(e, base, role)
        elif t in ("LWPOLYLINE", "POLYLINE"):
            self._poly(e, base, role)
        elif t == "CIRCLE" and role not in SKIP_GEOM_ROLES:
            c, r = e.dxf.center, float(e.dxf.radius)
            self.geom["circles"].append([round(c.x, 3), round(c.y, 3), round(r, 3), layer])
        elif t == "ARC" and role not in SKIP_GEOM_ROLES:
            c = e.dxf.center
            self.geom["arcs"].append([round(c.x, 3), round(c.y, 3), round(float(e.dxf.radius), 3),
                                      round(float(e.dxf.start_angle), 3), round(float(e.dxf.end_angle), 3), layer])
        elif t == "ELLIPSE" and role not in SKIP_GEOM_ROLES:
            c, major = e.dxf.center, e.dxf.major_axis
            self.geom["ellipses"].append([round(c.x, 3), round(c.y, 3), round(major.x, 3), round(major.y, 3),
                                          round(float(e.dxf.ratio), 4), layer])
        elif t == "INSERT":
            name = e.dxf.name
            ins = e.dxf.get("insert", Vec3())
            self.inserts.append({**base, "name": name, "at": _pt(ins), "xscale": round(e.dxf.get("xscale", 1), 4)})
            for att in e.attribs:
                self.visit(att, layout, depth, block_path + (handle,))
            if depth < MAX_DEPTH:
                try:
                    for ve in e.virtual_entities():
                        self.visit(ve, layout, depth + 1, block_path + (handle,))
                except Exception as exc:
                    runlog.warn("read", f"cannot expand block {name}: {type(exc).__name__}")
        else:
            self._drop(t, layer)

    def _line(self, e, base, role):
        s, en = e.dxf.start, e.dxf.end
        if role in KEEP_LINE_ROLES:
            self.lines.append({**base, "a": _pt(s), "b": _pt(en)})
        elif role not in SKIP_GEOM_ROLES:
            self.geom["lines"].append([round(s.x, 3), round(s.y, 3), round(en.x, 3), round(en.y, 3), base["layer"]])
        else:
            self._drop("LINE", base["layer"])

    def _poly(self, e, base, role):
        got = _metrics(e, self.tol)
        if got is None:
            self._drop(e.dxftype(), base["layer"])
            return
        pts, length, area, n, closed = got
        row = {**base, "closed": closed, "pts": pts, "n": n, "length": length, "area": area}
        if role in KEEP_POLY_ROLES:
            self.polys.append(row)
        elif role not in SKIP_GEOM_ROLES:
            self.geom["polys"].append(row)
        else:
            self._drop(e.dxftype(), base["layer"])

    def _table(self, e, base):
        """Cell text of an ACAD_TABLE, with its row and column. The table block is not expanded again."""
        try:
            ves = list(e.virtual_entities())
        except Exception as exc:
            self._drop("ACAD_TABLE", base["layer"])
            runlog.warn("read", f"table {base['handle']}: {type(exc).__name__}")
            return
        xs, ys = set(), set()
        for v in ves:
            if v.dxftype() != "LINE":
                continue
            a, b = v.dxf.start, v.dxf.end
            if abs(a.y - b.y) <= 1e-6:
                ys.add(round(a.y, 3))
            elif abs(a.x - b.x) <= 1e-6:
                xs.add(round(a.x, 3))
        xs, ys = sorted(xs), sorted(ys, reverse=True)

        def band(val, edges):
            for i in range(len(edges) - 1):
                lo, hi = sorted((edges[i], edges[i + 1]))
                if lo - 1e-6 <= val <= hi + 1e-6:
                    return i
            return None

        cells, seen = [], set()
        extra = []
        for v in ves:
            if v.dxftype() == "INSERT":
                try:
                    extra.extend(s for s in v.virtual_entities() if s.dxftype() == "MTEXT")
                except Exception:
                    continue
        for v in ves + extra:
            if v.dxftype() != "MTEXT":
                continue
            res = decode_mtext(v.text, self._font(v))
            if not res.decoded:
                continue
            p = v.dxf.insert
            r, c = band(p.y, ys), band(p.x, xs)
            key = (r, c, res.decoded)
            if key in seen:
                continue
            seen.add(key)
            cells.append({"r": r, "c": c, "text": res.decoded, "raw": res.plain_raw, "at": _pt(p)})
            self._add_text({**base, "table": base["handle"], "cell": [r, c]}, "MTEXT", p,
                           v.dxf.get("char_height", 0), 0, res, v)
        self.tables.append({**base, "n_rows": max(len(ys) - 1, 0), "n_cols": max(len(xs) - 1, 0),
                            "bbox": [xs[0], ys[-1], xs[-1], ys[0]] if xs and ys else None, "cells": cells})

    def _leader(self, e, base):
        try:
            content = e.get_mtext_content() or ""
        except Exception:
            content = ""
        ctx = getattr(e, "context", None)
        at, h, arrow = None, 0, None
        if ctx is not None:
            mtext = getattr(ctx, "mtext", None)
            if mtext is not None and getattr(mtext, "insert", None) is not None:
                at = mtext.insert
            elif getattr(ctx, "base_point", None) is not None:
                at = ctx.base_point
            h = getattr(ctx, "char_height", 0) or 0
            try:
                leaders = getattr(ctx, "leaders", None) or []
                if leaders and leaders[0].lines and leaders[0].lines[0].vertices:
                    arrow = _pt(leaders[0].lines[0].vertices[0])
            except Exception:
                arrow = None
        res = decode_mtext(content, None)
        if at is None or not res.decoded:
            self._drop("MULTILEADER", base["layer"])
            return
        self._add_text({**base, "leader": True, "arrow": arrow}, "MULTILEADER", at, h, 0, res)

    def _hatch(self, e, base):
        from functools import reduce
        from shapely.geometry import Polygon
        rings = []
        try:
            paths = list(ezpath.from_hatch(e))
        except Exception:
            self._drop("HATCH without a usable boundary", base["layer"])
            return
        for p in paths:
            pts = [(float(v.x), float(v.y)) for v in p.flattening(distance=self.tol)]
            if len(pts) < 3:
                continue
            poly = Polygon(pts).buffer(0)
            if not poly.is_empty:
                rings.append(poly)
        if not rings:
            self._drop("HATCH without a usable boundary", base["layer"])
            return
        try:
            geom = reduce(lambda a, b: a.symmetric_difference(b), sorted(rings, key=lambda g: -g.area))
            c = geom.representative_point()
        except Exception:
            self._drop("HATCH without a usable boundary", base["layer"])
            return
        outline, holes = outlines_of(geom, self.tol)
        self.geom["hatches"].append({**base, "pattern": e.dxf.get("pattern_name", ""),
                                     "solid": bool(e.dxf.get("solid_fill", 0)), "area_du2": round(float(geom.area), 3),
                                     "bbox": [round(v, 3) for v in geom.bounds], "rings": len(rings),
                                     "outline": outline, "holes": holes,
                                     "at": [round(c.x, 3), round(c.y, 3)]})

    def _add_text(self, base, t, insert, height, rotation, res, entity=None):
        if not res.decoded:
            return
        row = {**base, "type": t, "at": _pt(insert), "h": round(float(height or 0), 3),
               "rot": round(float(rotation or 0), 2), "raw": res.plain_raw, "text": res.decoded,
               "code_text": fold_homoglyphs(res.decoded), "scheme": res.scheme,
               "conf": res.confidence, "fonts": res.fonts}
        if t == "MTEXT":
            n_lines = max(1, res.decoded.count("\n") + 1)
            width = float(entity.dxf.get("width", 0) or 0) if entity is not None else 0
            attach = int(entity.dxf.get("attachment_point", 1) or 1) if entity is not None else 1
            box, estimated = mtext_bbox(insert, attach, width, row["h"], n_lines, row["rot"])
            row.update({"attach": attach, "width": round(width, 3), "n_lines": n_lines, "bbox": box,
                        "bbox_estimated": estimated})
        self.texts.append(row)


def _dropped_rows(counter: Counter) -> list[dict]:
    rows = []
    for (kind, layer), n in counter.most_common():
        rows.append({"type": kind, "layer": layer, "count": n})
    return rows


def dump(dxf_path) -> tuple[dict, dict]:
    doc = _open(dxf_path)
    d = Dumper(doc, _flat_tol(doc))
    for layout in doc.layouts:
        for e in layout:
            d.visit(e, layout.name, 0, ())
    ext_min, ext_max = doc.header.get("$EXTMIN", None), doc.header.get("$EXTMAX", None)
    layers = []
    for name, n in d.layer_counts.most_common():
        raw = name
        fixed = L.fix_mojibake(L.stem(name))
        layers.append({"name": raw, "name_fixed": fixed if fixed != L.stem(name) else None,
                       "stem": L.stem(name), "role": L.role(name), "count": n,
                       **d.layer_state.get(name, {"frozen": False, "off": False})})
    by_type = Counter()
    for (kind, _layer), n in d.dropped.items():
        by_type[kind] += n
    data = {
        "reader_version": READER_VERSION,
        "dxf": str(dxf_path), "insunits": doc.header.get("$INSUNITS", None),
        "extmin": _pt(ext_min) if ext_min else None, "extmax": _pt(ext_max) if ext_max else None,
        "styles": d.fonts, "layers": layers, "texts": d.texts, "dims": d.dims, "lines": d.lines,
        "polys": d.polys, "inserts": d.inserts, "tables": d.tables,
        "geom_counts": {k: len(v) for k, v in d.geom.items()},
        "dropped": _dropped_rows(d.dropped),
        "dropped_by_type": dict(by_type),
    }
    return data, d.geom


def dump_path_for(file_sha: str):
    return config.CACHE_DIR / "sheets" / f"{file_sha[:12]}.json"


def geom_path_for(file_sha: str):
    return config.CACHE_DIR / "sheets" / f"{file_sha[:12]}.geom.json"


def load_dump(file_sha: str) -> dict | None:
    p = dump_path_for(file_sha)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def dump_all(register: dict, force: bool = False) -> dict:
    from .oda import dxf_path_for
    out = {}
    with runlog.stage("read"):
        for f in register["files"]:
            if f["kind"] != "drawing_cad":
                continue
            dxf = dxf_path_for(f["sha256"])
            target = dump_path_for(f["sha256"])
            fresh = target.exists() and not force
            if fresh:
                try:
                    fresh = json.loads(target.read_text(encoding="utf-8")).get("reader_version") == READER_VERSION
                except (OSError, json.JSONDecodeError):
                    fresh = False
            if fresh:
                out[f["sha256"]] = str(target)
                continue
            if not dxf.exists():
                runlog.warn("read", f"no DXF for {f['name']}", file=f["rel"])
                continue
            data, geom = dump(dxf)
            data["file"] = f["rel"]
            data["sha256"] = f["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            geom_path_for(f["sha256"]).write_text(json.dumps(geom, ensure_ascii=False), encoding="utf-8")
            summary = {"texts": len(data["texts"]), "tables": len(data["tables"]), "geom_counts": data["geom_counts"],
                       "dropped_by_type": data["dropped_by_type"]}
            (config.CACHE_DIR / "sheets" / f"{f['sha256'][:12]}.read.json").write_text(
                json.dumps(summary, ensure_ascii=False), encoding="utf-8")
            undecoded = sum(1 for t in data["texts"] if t["scheme"] != "unicode")
            dropped = sum(data["dropped_by_type"].values())
            runlog.event("read", "info", f"{f['name']}: {len(data['texts'])} texts ({undecoded} legacy-decoded), "
                         f"{len(data['tables'])} tables, {data['geom_counts'].get('hatches', 0)} hatches, "
                         f"{len(data['dims'])} dims, {dropped} entities still unread")
            out[f["sha256"]] = str(target)
    return out
