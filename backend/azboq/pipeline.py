"""All stages in order. Each stage stores its output; the API only reads stored outputs."""
import json
import re

from . import config, runlog, store
from .text import legacy
from .text.normalise import fold_key

STAGES = ["ingest", "bill", "conversion", "read", "sheets", "index", "source_map", "vision", "takeoff", "match",
          "operations"]


def stage_ingest():
    from .ingest.register import build_register
    reg = build_register()
    store.put("register", reg)
    return reg


def stage_bill():
    from .bill.parse import parse_bill
    bill = parse_bill()
    store.put("bill", bill)
    words = set()
    for line in bill["lines"]:
        for w in re.findall(r"[\wƏəÖöÜüÇçŞşĞğİı]{3,}", line["description"]):
            words.add(fold_key(w))
    for s in bill["sections"]:
        for w in re.findall(r"[\wƏəÖöÜüÇçŞşĞğİı]{3,}", s["title"]):
            words.add(fold_key(w))
    config.ensure_dirs()
    (config.CACHE_DIR / "az_vocab.json").write_text(json.dumps(sorted(words), ensure_ascii=False), encoding="utf-8")
    legacy.az_vocabulary.cache_clear()
    return bill


def stage_conversion():
    from .dwg.crosscheck import load_crosscheck
    from .dwg.oda import load_manifest
    reg = store.get("register")
    man, cross = load_manifest(), load_crosscheck()
    rows = []
    for f in reg["files"]:
        if f["kind"] != "drawing_cad":
            continue
        m, c = man.get(f["sha256"], {}), cross.get(f["sha256"], {})
        status = m.get("status", "not converted")
        if status in ("converted", "cached"):
            status = "read" if c.get("agree") else "reader disagreement"
        if m.get("status") == "failed":
            status = "failed"
        if status != "read":
            runlog.warn("conversion", f"{f['name']}: {status}", file=f["rel"])
        rows.append({"sha256": f["sha256"], "file": f["rel"], "name": f["name"], "status": status,
                     "oda": {k: m.get(k) for k in ("status", "reason", "modelspace_entities", "insunits", "acadver",
                                                   "auditor_errors", "seconds")},
                     "crosscheck": {k: c.get(k) for k in ("oda_total", "libredwg_total", "libredwg_status",
                                                          "libredwg_error", "type_diffs", "layer_diffs", "agree",
                                                          "layer_naming_differs", "total_diff")}})
    out = {"files": rows, "converter": str(config.ODA_EXE)}
    store.put("conversion", out)
    return out


def stage_read():
    from .dwg.read import dump_all
    from .pdf.read import dump_all_pdfs
    reg = store.get("register")
    dump_all(reg)
    dump_all_pdfs(reg)


def stage_sheets():
    from .dwg.read import load_dump
    from .pdf.read import load_pdf_dump
    from .sheets import detect_regions
    reg = store.get("register")
    out = {"dwg": {}, "pdf": {}}
    with runlog.stage("sheets"):
        for f in reg["files"]:
            if f["kind"] == "drawing_cad":
                d = load_dump(f["sha256"])
                if d is None:
                    continue
                regions = detect_regions(d, f.get("building", "site"), f.get("discipline", "unknown"))
                out["dwg"][f["sha256"]] = {"file": f["rel"], "regions": regions}
                for r in regions:
                    n = r["number"]
                    if n and n["order_typo"]:
                        near = abs(int(n["order"]) - 9335) <= 2
                        msg = (f"sheet number {n['raw']} looks like a typo of 9335" if near else
                               f"sheet {n['raw']} carries order {n['order']}: probably copied from another project")
                        runlog.warn("sheets", f"{msg} ({f['name']}, {r['id']})", file=f["rel"], region=r["id"])
            elif f["kind"] == "drawing_pdf":
                p = load_pdf_dump(f["sha256"])
                if p is None:
                    continue
                out["pdf"][f["sha256"]] = {"file": f["rel"], "pages": [
                    {k: pg[k] for k in ("page", "number", "building", "building_from", "discipline", "title", "mismatch")}
                    for pg in p["pages"]]}
    store.put("sheets", out)
    return out


def stage_index():
    from .dwg.read import load_dump
    from .index.numbers import build_index
    from .pdf.read import load_pdf_dump
    reg, sheets = store.get("register"), store.get("sheets")
    drawings, pdfs = [], []
    for f in reg["files"]:
        if f["kind"] == "drawing_cad":
            d = load_dump(f["sha256"])
            if d:
                drawings.append(d)
        elif f["kind"] == "drawing_pdf":
            p = load_pdf_dump(f["sha256"])
            if p:
                pdfs.append(p)
    regions = {sha: v["regions"] for sha, v in sheets["dwg"].items()}
    file_info = {f["sha256"]: f for f in reg["files"]}
    with runlog.stage("index"):
        idx = build_index(drawings, pdfs, regions, file_info)
        (config.CACHE_DIR / "number-index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
        runlog.event("index", "info", f"{len(idx)} numbers indexed, "
                     f"{sum(1 for e in idx if e['strength'] == 'strong')} strong")
    store.put("index_summary", {"count": len(idx), "strong": sum(1 for e in idx if e["strength"] == "strong")})
    return idx


def stage_source_map():
    from .sourcemap import build_source_map
    out = build_source_map()
    store.put("source_map", out)
    return out


def stage_vision():
    from .vision import run_vision
    out = run_vision()
    store.put("vision", out)
    return out


def stage_takeoff():
    from .engine.run import run_takeoff
    out = run_takeoff()
    store.put("takeoff", out)
    return out


def stage_match():
    from .match.run import run_match
    out = run_match()
    store.put("report", out)
    return out


def stage_operations():
    from .operations import build_operations
    out = build_operations()
    store.put("operations", out)
    return out


FUNCS = {"operations": stage_operations, "ingest": stage_ingest, "bill": stage_bill, "conversion": stage_conversion, "read": stage_read,
         "sheets": stage_sheets, "index": stage_index, "source_map": stage_source_map, "takeoff": stage_takeoff,
         "match": stage_match, "vision": stage_vision}


def run_all(only=None):
    runlog.reset()
    names = only or STAGES
    if "bill" not in names and store.get("bill") is None:
        names = ["bill"] + list(names)
    for name in STAGES:
        if name in names:
            FUNCS[name]()
    # Keep each stage's latest events, so a partial rerun does not hide earlier warnings.
    by_stage = store.get("runlog_stages") or {}
    fresh: dict = {}
    for e in runlog.events():
        fresh.setdefault(e["stage"], []).append(e)
    by_stage.update(fresh)
    store.put("runlog_stages", by_stage)
    events = [e for evs in by_stage.values() for e in evs]
    review = [{"stage": e["stage"], "severity": e["kind"], **{k: v for k, v in e.items() if k not in ("stage", "kind")}}
              for e in events if e["kind"] in ("warning", "error")]
    store.put("runlog", {"events": sorted(events, key=lambda e: e["t"]), "review": review})
    path = runlog.write_manifest({"stages": names})
    print(f"run manifest: {path}")
