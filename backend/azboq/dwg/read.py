"""Read one DXF into a compact dump: texts, dimensions, frames, table lines, inserts and layers.

Blocks are expanded to world coordinates so title-block and schedule text placed
inside blocks is not lost. Text is decoded per run with the run's own font.
"""
import json
import math
from collections import Counter

import ezdxf
from ezdxf import recover
from ezdxf.math import Vec3

from .. import config, runlog
from ..text.mtext import decode_mtext, decode_text
from ..text.normalise import fold_homoglyphs
from . import layers as L

MAX_DEPTH = 4
KEEP_LINE_ROLES = {"table", "frame"}
KEEP_POLY_ROLES = {"frame", "table", "wall", "partition", "column", "slab", "zone", "roof", "road", "fence", "survey",
                   "unclassified", "pipe"}


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


class Dumper:
    def __init__(self, doc):
        self.doc = doc
        self.fonts = _style_fonts(doc)
        self.texts, self.dims, self.lines, self.polys, self.inserts = [], [], [], [], []
        self.layer_counts = Counter()
        self.layer_state = {}
        for layer in doc.layers:
            self.layer_state[layer.dxf.name] = {"frozen": layer.is_frozen(), "off": not layer.is_on()}

    def _font(self, e) -> str:
        return self.fonts.get(str(e.dxf.get("style", "Standard")).lower(), "")

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
                return
            res = decode_text(e.dxf.get("text", ""), self._font(e))
            self._add_text(base, t, e.dxf.get("insert", Vec3()), e.dxf.get("height", 0), e.dxf.get("rotation", 0), res)
        elif t == "MTEXT":
            res = decode_mtext(e.text, self._font(e))
            self._add_text(base, t, e.dxf.get("insert", Vec3()), e.dxf.get("char_height", 0), e.dxf.get("rotation", 0), res)
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
        elif t == "LINE" and role in KEEP_LINE_ROLES:
            s, en = e.dxf.start, e.dxf.end
            self.lines.append({**base, "a": _pt(s), "b": _pt(en)})
        elif t == "LWPOLYLINE" and role in KEEP_POLY_ROLES:
            pts = [_pt(p) for p in e.get_points("xy")]
            if len(pts) >= 2:
                self.polys.append({**base, "closed": bool(e.closed), "pts": pts if len(pts) <= 400 else pts[:400],
                                   "n": len(pts)})
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

    def _add_text(self, base, t, insert, height, rotation, res):
        if not res.decoded:
            return
        self.texts.append({**base, "type": t, "at": _pt(insert), "h": round(float(height or 0), 3),
                           "rot": round(float(rotation or 0), 2), "raw": res.plain_raw, "text": res.decoded,
                           "code_text": fold_homoglyphs(res.decoded), "scheme": res.scheme,
                           "conf": res.confidence, "fonts": res.fonts})


def dump(dxf_path) -> dict:
    doc = _open(dxf_path)
    d = Dumper(doc)
    for layout in doc.layouts:
        for e in layout:
            d.visit(e, layout.name, 0, ())
    ext_min, ext_max = doc.header.get("$EXTMIN", None), doc.header.get("$EXTMAX", None)
    layers = []
    for name, n in d.layer_counts.most_common():
        layers.append({"name": name, "stem": L.stem(name), "role": L.role(name), "count": n,
                       **d.layer_state.get(name, {"frozen": False, "off": False})})
    return {
        "dxf": str(dxf_path), "insunits": doc.header.get("$INSUNITS", None),
        "extmin": _pt(ext_min) if ext_min else None, "extmax": _pt(ext_max) if ext_max else None,
        "styles": d.fonts, "layers": layers, "texts": d.texts, "dims": d.dims, "lines": d.lines,
        "polys": d.polys, "inserts": d.inserts,
    }


def dump_path_for(file_sha: str):
    return config.CACHE_DIR / "sheets" / f"{file_sha[:12]}.json"


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
            if target.exists() and not force:
                out[f["sha256"]] = str(target)
                continue
            if not dxf.exists():
                runlog.warn("read", f"no DXF for {f['name']}", file=f["rel"])
                continue
            data = dump(dxf)
            data["file"] = f["rel"]
            data["sha256"] = f["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            undecoded = sum(1 for t in data["texts"] if t["scheme"] != "unicode")
            runlog.event("read", "info", f"{f['name']}: {len(data['texts'])} texts ({undecoded} legacy-decoded), "
                         f"{len(data['dims'])} dims, {len(data['polys'])} polylines")
            out[f["sha256"]] = str(target)
    return out
