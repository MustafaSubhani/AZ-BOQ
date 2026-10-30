"""HTTP API. Reads stored stage outputs; converts and measures nothing at request time."""
import json
from functools import lru_cache
from pathlib import Path

import pymupdf
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import config, store
from ..text import translate

app = FastAPI(title="AZ-BOQ demo")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


def _need(name: str):
    data = store.get(name)
    if data is None:
        raise HTTPException(404, f"stage '{name}' has not run yet")
    return data


@lru_cache(maxsize=1)
def _files_by_sha() -> dict:
    return {f["sha256"]: f for f in _need("register")["files"]}


@app.get("/api/summary")
def summary():
    report = store.get("report") or {}
    conv = store.get("conversion") or {"files": []}
    bill = store.get("bill") or {}
    take = store.get("takeoff") or {"items": []}
    runlog = store.get("runlog") or {"review": []}
    return {
        "counts": report.get("counts", {}),
        "drawings_not_read": sum(1 for f in conv["files"] if f["status"] != "read"),
        "drawings_total": len(conv["files"]),
        "inputs_missing": sum(1 for i in take["items"] if i["value"]["status"] == "blocked"),
        "values_from_rules": take.get("rule_count", 0),
        "reader_disagreements": sum(1 for f in conv["files"] if f["status"] == "reader disagreement"),
        "conflicts": len(take.get("conflicts", [])),
        "review_items": len(runlog["review"]),
        "bill": {"lines": len(bill.get("lines", [])), "sections": len(bill.get("sections", [])),
                 "line_sum": bill.get("line_sum"), "chain": bill.get("chain"), "totals": bill.get("totals")},
        "value_by_building": report.get("value_by_building", []),
        "attention": report.get("attention", []),
    }


@lru_cache(maxsize=64)
def _page_count(path: str) -> int:
    # The raw package (data/) is not shipped with the caches; a missing file has no pages to list.
    if not Path(path).exists():
        return 0
    return len(pymupdf.open(path))


@app.get("/api/register")
def register():
    reg = _need("register")
    conv = {f["sha256"]: f for f in (store.get("conversion") or {"files": []})["files"]}
    sheets = store.get("sheets") or {"dwg": {}, "pdf": {}}
    files = []
    for f in reg["files"]:
        row = dict(f)
        row.pop("path", None)
        summary_path = config.CACHE_DIR / "sheets" / f"{f['sha256'][:12]}.read.json"
        if summary_path.exists():
            row["reader"] = json.loads(summary_path.read_text(encoding="utf-8"))
        if f["sha256"] in conv:
            row["read_status"] = conv[f["sha256"]]["status"]
            row["crosscheck"] = conv[f["sha256"]]["crosscheck"]
            row["oda"] = conv[f["sha256"]]["oda"]
        if f["sha256"] in sheets["dwg"]:
            row["sheets"] = [{k: r.get(k) for k in ("id", "number", "building", "building_from", "discipline", "title",
                                                    "scale", "paper", "method", "text_count", "copy_of", "only_other_order")}
                             for r in sheets["dwg"][f["sha256"]]["regions"]]
        elif f["sha256"] in sheets["pdf"]:
            row["sheets"] = sheets["pdf"][f["sha256"]]["pages"]
        elif f["kind"] in ("drawing_scan", "explanatory_note_scan", "estimate_scan"):
            row["sheets"] = [{"page": p, "kind": "scan", "title": None, "building": f.get("building")}
                             for p in range(f.get("pages") or _page_count(f["path"]))]
        files.append(row)
    return {"files": files, "duplicates": reg["duplicates"], "counts": reg["counts"], "total": reg["total"]}


@app.get("/api/line/{line_id}/explain")
def explain_line(line_id: str):
    from ..match.explain import explain_line as build
    data = build(line_id, _need("bill"), _need("report"), _need("takeoff"))
    if data is None:
        raise HTTPException(404, "no such line")
    return data


@app.get("/api/bill")
def bill():
    b = _need("bill")
    report = store.get("report") or {"lines": {}}
    floors = (store.get("floors") or {"lines": {}})["lines"]
    lines = []
    for l in b["lines"]:
        row = {k: l[k] for k in ("id", "row", "section", "item", "description", "unit_raw", "unit", "unit_known", "qty",
                                  "rate", "amount", "building", "trade", "comment")}
        row["check"] = report["lines"].get(l["id"])
        row["floor"] = floors.get(l["id"])
        lines.append(row)
    sections = [{k: s.get(k) for k in ("code", "stored_code", "row", "title", "trade", "building", "code_repaired",
                                              "parent", "mark")}
                for s in b["sections"]]
    return {"sections": sections, "lines": lines, "totals": b["totals"], "chain": b["chain"],
            "line_sum": b["line_sum"], "unknown_units": b["unknown_units"], "external_links": b["external_links"]}


@app.get("/api/takeoff")
def takeoff():
    return _need("takeoff")


@app.get("/api/report")
def report():
    return _need("report")


@app.get("/api/coverage")
def coverage():
    return _need("source_map")


@app.get("/api/runlog")
def runlog():
    return store.get("runlog") or {"events": [], "review": []}


@app.get("/api/conversion")
def conversion():
    return _need("conversion")


@app.post("/api/translations")
def translations(texts: list[str] = Body(...), lang: str = "en"):
    return translate.lookup(texts[:2000], lang)


@app.post("/api/translations/correct")
def translation_correct(payload: dict = Body(...)):
    translate.correct(payload["source"], payload["text"])
    return {"ok": True}


@app.get("/api/drawing/{sha}/regions")
def drawing_regions(sha: str):
    sheets = _need("sheets")
    full = next((k for k in sheets["dwg"] if k.startswith(sha)), None)
    if not full:
        raise HTTPException(404, "not a converted drawing")
    return {"file": sheets["dwg"][full]["file"], "sha256": full, "regions": sheets["dwg"][full]["regions"]}


@app.get("/api/drawing/{sha}/region/{rid}/meta")
def drawing_region_meta(sha: str, rid: str):
    from ..dwg.oda import dxf_path_for
    from ..dwg.render import render_region, tile_path
    info = drawing_regions(sha)
    region = next((r for r in info["regions"] if r["id"] == rid), None)
    if region is None:
        raise HTTPException(404, "no such region")
    meta = render_region(str(dxf_path_for(info["sha256"])), region["bbox"], tile_path(info["sha256"], rid))
    from ..dwg.read import load_dump
    d = load_dump(info["sha256"])
    x0, y0, x1, y1 = region["bbox"]
    texts = [{"handle": t["handle"], "text": t["text"], "raw": t["raw"], "scheme": t["scheme"], "at": t["at"],
              "layer": t["layer"]}
             for t in d["texts"] if x0 <= t["at"][0] <= x1 and y0 <= t["at"][1] <= y1][:3000]
    return {**meta, "region": region, "texts": texts, "png_url": f"/api/drawing/{sha}/region/{rid}.png"}


@app.get("/api/drawing/{sha}/region/{rid}/shapes")
def drawing_shapes(sha: str, rid: str):
    from ..areas import region_shapes
    meta = drawing_region_meta(sha, rid)
    return region_shapes(sha, rid, meta, store.get("takeoff"), store.get("report"))


@app.get("/api/areas")
def areas():
    from ..areas import area_book
    return area_book(_need("register"), store.get("takeoff"), store.get("report"), store.get("sheets") or {})


@app.get("/api/drawing/{sha}/region/{rid}.png")
def drawing_region_png(sha: str, rid: str):
    meta = drawing_region_meta(sha, rid)
    return FileResponse(meta["png"], media_type="image/png")


@app.get("/api/drawing/{sha}/entity/{handle}")
def drawing_entity(sha: str, handle: str):
    from ..dwg.read import load_dump
    info = drawing_regions(sha)
    d = load_dump(info["sha256"])
    for coll in ("texts", "dims", "polys", "lines", "inserts"):
        for e in d[coll]:
            if e.get("handle") == handle:
                from ..sheets import region_of
                at = e.get("at") or (e.get("pts") or [[0, 0]])[0]
                return {"collection": coll, "entity": e, "region": region_of(at, info["regions"])}
    raise HTTPException(404, "handle not found")


@app.get("/api/pdf/{sha}/page/{page}.png")
def pdf_page_png(sha: str, page: int):
    f = next((v for k, v in _files_by_sha().items() if k.startswith(sha)), None)
    if not f:
        raise HTTPException(404, "file not found")
    out = config.TILES_DIR / f"{f['sha256'][:12]}_p{page}.png"
    if not out.exists():
        doc = pymupdf.open(f["path"])
        doc[page].get_pixmap(dpi=110).save(str(out))
    return FileResponse(str(out), media_type="image/png")


@app.get("/api/pdf/{sha}/page/{page}/meta")
def pdf_page_meta(sha: str, page: int):
    from ..pdf.read import load_pdf_dump
    f = next((v for k, v in _files_by_sha().items() if k.startswith(sha)), None)
    if not f:
        raise HTTPException(404, "file not found")
    d = load_pdf_dump(f["sha256"])
    from ..crops import pdf_transform
    if d is None:
        doc = pymupdf.open(f["path"])
        p = doc[page]
        return {"width": p.rect.width, "height": p.rect.height, "lines": [], "png_url": f"/api/pdf/{sha}/page/{page}.png",
                "scanned": True, "transform": pdf_transform()}
    pg = d["pages"][page]
    return {"width": pg["width"], "height": pg["height"], "lines": pg["lines"], "number": pg.get("number"),
            "building": pg.get("building"), "png_url": f"/api/pdf/{sha}/page/{page}.png",
            "transform": pdf_transform()}


@app.get("/api/exports")
def exports():
    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = config.EXPORT_DIR / "exports.json"
    info = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    files = [{"name": p.name, "size": p.stat().st_size} for p in sorted(config.EXPORT_DIR.glob("*.*"))
             if p.suffix in (".xlsx", ".pdf")]
    return {"files": files, "info": info}


@app.api_route("/api/exports/file/{name}", methods=["GET", "HEAD"])
def export_file(name: str):
    p = (config.EXPORT_DIR / name).resolve()
    if p.parent != config.EXPORT_DIR.resolve() or not p.exists():
        raise HTTPException(404, "no such export")
    return FileResponse(str(p), filename=name)


@app.get("/api/vision")
def vision():
    return store.get("vision") or {"files": [], "model": None}


@app.get("/api/operations")
def operations():
    return _need("operations") if store.get("operations") else {"registers": []}


@app.get("/api/reviews")
def reviews(target: str | None = None):
    from ..reviews import active_reviews
    rows = active_reviews()
    if target:
        rows = [row for row in rows if row["target_id"] == target or str(row["target_id"]).startswith(target)]
    return {"reviews": rows}


@app.post("/api/review")
def review_add(payload: dict = Body(...)):
    from ..pipeline import stage_match, stage_reviews
    from ..reviews import ExprError, add_review
    try:
        review_id = add_review(payload["target_kind"], payload["target_id"], payload["action"],
                               payload.get("payload") or {}, payload.get("reason") or "", payload.get("author") or "")
    except (ExprError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    stage_reviews()
    stage_match()
    return {"id": review_id}


@app.delete("/api/review/{review_id}")
def review_supersede(review_id: int, payload: dict = Body(...)):
    from ..pipeline import stage_match, stage_reviews
    from ..reviews import ExprError, supersede
    try:
        reset_id = supersede(review_id, payload.get("author") or "", payload.get("reason") or "")
    except ExprError as exc:
        raise HTTPException(400, str(exc)) from exc
    stage_reviews()
    stage_match()
    return {"id": reset_id}


_dist = config.ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
