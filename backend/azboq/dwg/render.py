"""Render one sheet region of a DXF to PNG for the viewer.

Legacy-font text is decoded and redrawn in a Unicode font, hatch-debris, hidden
and frozen layers are left out, and lines are drawn black, so the sheet reads
like a plot instead of a screen dump. Measurement never uses these images.
"""
from collections import OrderedDict
from pathlib import Path

import ezdxf
from ezdxf import recover
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing import config as dcfg
from ezdxf.addons.drawing import pymupdf as pmb
from ezdxf.math import BoundingBox2d

from .. import config
from ..text.mtext import decode_mtext, decode_text
from . import layers as L

SKIP_ROLES = {"hatch", "hidden"}
UNI_STYLE = "AZBOQ_UNICODE"
_docs: "OrderedDict[str, object]" = OrderedDict()


def _load(dxf_path: str):
    if dxf_path in _docs:
        _docs.move_to_end(dxf_path)
        return _docs[dxf_path]
    try:
        doc = ezdxf.readfile(dxf_path)
    except ezdxf.DXFStructureError:
        doc, _ = recover.readfile(dxf_path)
    _decode_in_place(doc)
    _docs[dxf_path] = doc
    while len(_docs) > 2:
        _docs.popitem(last=False)
    return doc


def _decode_in_place(doc):
    if UNI_STYLE not in doc.styles:
        doc.styles.new(UNI_STYLE, dxfattribs={"font": "arial.ttf"})
    fonts = {st.dxf.name.lower(): st.dxf.get("font", "") for st in doc.styles}

    # SHX styles have no glyph for ə, ş, ğ..., so any non-ASCII text moves to the Unicode style.
    def fix(e):
        t = e.dxftype()
        if t in ("TEXT", "ATTRIB", "ATTDEF"):
            res = decode_text(e.dxf.get("text", ""), fonts.get(str(e.dxf.get("style", "")).lower()))
            if res.scheme != "unicode":
                e.dxf.text = res.decoded
            if res.scheme != "unicode" or not res.decoded.isascii():
                e.dxf.style = UNI_STYLE
        elif t == "MTEXT":
            res = decode_mtext(e.text, fonts.get(str(e.dxf.get("style", "")).lower()))
            if res.scheme != "unicode":
                e.text = res.decoded.replace("\n", "\\P")
            if res.scheme != "unicode" or not res.decoded.isascii():
                e.dxf.style = UNI_STYLE
        if t == "INSERT":
            for a in e.attribs:
                fix(a)

    for e in doc.modelspace():
        fix(e)
    for block in doc.blocks:
        for e in block:
            fix(e)


def _anchor(e):
    d = e.dxf
    for attr in ("insert", "start", "center", "defpoint"):
        if d.hasattr(attr):
            v = d.get(attr)
            return float(v[0]), float(v[1])
    if e.dxftype() == "LWPOLYLINE":
        pts = list(e.get_points("xy"))
        if pts:
            return float(pts[0][0]), float(pts[0][1])
    return None


_index: dict[str, list] = {}


def _entity_index(dxf_path: str, doc) -> list:
    """Visible model-space entities with their anchor, built once per drawing (None = no anchor, always drawn)."""
    if dxf_path not in _index:
        hidden_layers = {l.dxf.name for l in doc.layers if l.is_frozen() or not l.is_on()}
        roles: dict[str, bool] = {}
        rows = []
        for e in doc.modelspace():
            layer = e.dxf.get("layer", "0")
            if layer not in roles:
                roles[layer] = layer not in hidden_layers and L.role(layer) not in SKIP_ROLES
            if roles[layer]:
                rows.append((e, _anchor(e)))
        _index.clear()
        _index[dxf_path] = rows
    return _index[dxf_path]


def render_region(dxf_path: str, bbox, out: Path, width_px: int = 2400) -> dict:
    x0, y0, x1, y1 = bbox
    if out.exists():
        return _meta(bbox, out)
    doc = _load(dxf_path)
    pad_x, pad_y = (x1 - x0) * 0.02, (y1 - y0) * 0.02
    lo_x, hi_x, lo_y, hi_y = x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y
    keep_ids = {id(e) for e, a in _entity_index(dxf_path, doc)
                if a is None or (lo_x <= a[0] <= hi_x and lo_y <= a[1] <= hi_y)}

    cfg = dcfg.Configuration(background_policy=dcfg.BackgroundPolicy.WHITE, color_policy=dcfg.ColorPolicy.BLACK,
                             lineweight_scaling=0.6, hatch_policy=dcfg.HatchPolicy.SHOW_OUTLINE)
    backend = pmb.PyMuPdfBackend()
    # draw_layout (not draw_entities) so the white background and the layout's redraw order are applied.
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(
        doc.modelspace(), finalize=True, filter_func=lambda e: id(e) in keep_ids)
    w_mm = 420.0
    h_mm = w_mm * (y1 - y0) / (x1 - x0) if x1 > x0 else 297.0
    page = layout.Page(w_mm, h_mm, layout.Units.mm, margins=layout.Margins.all(0))
    dpi = int(width_px / (w_mm / 25.4))
    png = backend.get_pixmap_bytes(page, fmt="png", dpi=dpi, render_box=BoundingBox2d([(x0, y0), (x1, y1)]),
                                   settings=layout.Settings(fit_page=True))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png)
    return _meta(bbox, out)


def _meta(bbox, out: Path) -> dict:
    from PIL import Image
    from ..crops import region_transform
    with Image.open(out) as im:
        w, h = im.size
    return {"png": str(out), "width": w, "height": h, "bbox": list(bbox),
            "transform": region_transform(list(bbox), w, h)}


def render_all(sheets: dict, dxf_path_for, log) -> dict:
    """Pre-render every sheet region, one drawing at a time so each DXF loads once."""
    done, failed = 0, []
    for sha, info in sheets["dwg"].items():
        for r in info["regions"]:
            out = tile_path(sha, r["id"])
            if out.exists():
                done += 1
                continue
            try:
                render_region(str(dxf_path_for(sha)), r["bbox"], out)
                if not _paper_is_white(out):
                    raise RuntimeError("tile background is not white; the renderer did not draw a paper")
                done += 1
            except Exception as exc:  # noqa: BLE001 - one bad region must not stop the others; it is logged
                failed.append({"file": info["file"], "region": r["id"], "error": repr(exc)})
                log(f"{info['file']} {r['id']}: render failed: {exc!r}")
        _docs.clear()
        _index.clear()
    return {"rendered": done, "failed": failed}


def _paper_is_white(png: Path) -> bool:
    from PIL import Image
    # A plotted sheet is mostly paper; frame lines can run through the corners, so sample the whole tile.
    with Image.open(png) as im:
        small = im.convert("L").resize((64, 64))
        light = sum(1 for v in small.tobytes() if v > 200)
    return light > 64 * 64 * 0.5


def tile_path(file_sha: str, region_id: str) -> Path:
    return config.TILES_DIR / f"{file_sha[:12]}_{region_id}.png"
