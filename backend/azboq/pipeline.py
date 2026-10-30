"""All stages in order. Each stage stores its output; the API only reads stored outputs."""
import json
import re

from . import config, runlog, store
from .text import legacy
from .text.normalise import fold_key

STAGES = ["ingest", "bill", "conversion", "read", "sheets", "schedules", "index", "source_map", "vision", "takeoff",
          "reviews", "match", "floors", "operations"]


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
    from .dwg.crosscheck import load_crosscheck, reading_status
    from .dwg.oda import load_manifest
    reg = store.get("register")
    man, cross = load_manifest(), load_crosscheck()
    rows = []
    for f in reg["files"]:
        if f["kind"] != "drawing_cad":
            continue
        m, c = man.get(f["sha256"], {}), cross.get(f["sha256"], {})
        status = reading_status(m.get("status", "not converted"), c)
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
    from .sheets import assign_families, copy_differences, detect_regions
    reg = store.get("register")
    out = {"dwg": {}, "pdf": {}}
    with runlog.stage("sheets"):
        for f in reg["files"]:
            if f["kind"] == "drawing_cad":
                d = load_dump(f["sha256"])
                if d is None:
                    continue
                regions = detect_regions(d, f.get("building", "site"), f.get("discipline", "unknown"))
                diffs = copy_differences(d["texts"], regions)
                out["dwg"][f["sha256"]] = {"file": f["rel"], "regions": regions, "copy_diffs": diffs}
                for r in regions:
                    n = r.get("number") or {}
                    if r.get("copy_of"):
                        continue
                    if r.get("only_other_order") and n:
                        runlog.warn("sheets", f"sheet {n.get('raw')} is the only copy and carries order {n.get('order')}; "
                                    f"kept, but its values stay in review ({f['name']}, {r['id']})",
                                    file=f["rel"], region=r["id"])
                    elif n and n.get("order_typo"):
                        runlog.warn("sheets", f"sheet {n.get('raw')} carries order {n.get('order')} and no 9335 copy was found "
                                    f"({f['name']}, {r['id']})", file=f["rel"], region=r["id"])
                for diff in diffs:
                    runlog.warn("sheets", f"{f['name']}: {diff['sheet']} differs from {diff['canonical_sheet']} "
                                f"(only on the copy: {diff['only_on_copy']}; only on the canonical: {diff['only_on_canonical']})",
                                file=f["rel"], region=diff["copy"])
            elif f["kind"] == "drawing_pdf":
                p = load_pdf_dump(f["sha256"])
                if p is None:
                    continue
                for pg in p["pages"]:
                    pg["id"] = f"P{pg['page']}"
                assign_families(p["pages"])
                out["pdf"][f["sha256"]] = {"file": f["rel"], "pages": [
                    {k: pg.get(k) for k in ("page", "id", "number", "building", "building_from", "discipline", "title",
                                            "mismatch", "family", "copy_of", "only_other_order")}
                    for pg in p["pages"]]}
    store.put("sheets", out)
    return out


def stage_schedules():
    import json
    from pathlib import Path
    from .schedules.tables import read_pdf
    reg = store.get("register")
    with runlog.stage("schedules"):
        for f in reg["files"]:
            if f["kind"] != "drawing_pdf":
                continue
            if not f.get("path") or not Path(f["path"]).exists():
                runlog.warn("schedules", f"{f['name']}: the PDF is not on this machine, so its ruled tables were not read",
                            file=f["rel"])
                continue
            tables = read_pdf(f["path"])
            from .schedules.rooms import read_rooms
            rooms = read_rooms(f["path"])
            target = config.CACHE_DIR / "pdf" / f"{f['sha256'][:12]}.schedules.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"file": f["rel"], "sha256": f["sha256"], "tables": tables, "rooms": rooms},
                                         ensure_ascii=False), encoding="utf-8")
            areas = sum(1 for t in tables for row in t["rows"] if not row.get("section")
                        for cell in row["cells"] if cell.get("unit") == "m²")
            runlog.event("schedules", "info", f"{f['name']}: {len(tables)} ruled tables, {areas} area cells, "
                         f"{sum(len(s['rows']) for s in rooms)} room rows")
        from .dwg.read import load_dump
        from .schedules.acad import acad_tables
        from .schedules.grids import grids_in_dump
        for f in reg["files"]:
            if f["kind"] != "drawing_cad":
                continue
            dump = load_dump(f["sha256"])
            if not dump:
                continue
            grids = grids_in_dump(dump)
            acad = acad_tables(dump)
            target = config.CACHE_DIR / "sheets" / f"{f['sha256'][:12]}.schedules.json"
            target.write_text(json.dumps({"file": f["rel"], "sha256": f["sha256"], "tables": grids + acad},
                                         ensure_ascii=False), encoding="utf-8")
            if grids:
                runlog.event("schedules", "info", f"{f['name']}: {len(grids)} line-grid tables")
            if acad:
                runlog.event("schedules", "info", f"{f['name']}: {len(acad)} acad tables")


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


def stage_reviews():
    from . import runlog
    from .reviews import apply_to_takeoff
    with runlog.stage("reviews"):
        ids = apply_to_takeoff()
        runlog.event("reviews", "info", f"{len(ids)} reviews applied" if ids else "no reviews")
    return ids


def stage_match():
    from .match.run import run_match
    out = run_match()
    store.put("report", out)
    return out


def stage_floors():
    from .floors import build_floors
    with runlog.stage("floors"):
        out = build_floors()
        store.put("floors", out)
        runlog.event("floors", "info", ", ".join(f"{k} {v}" for k, v in sorted(out["counts"].items())))
    return out


def stage_operations():
    from .operations import build_operations
    out = build_operations()
    store.put("operations", out)
    return out


FUNCS = {"operations": stage_operations, "ingest": stage_ingest, "bill": stage_bill, "conversion": stage_conversion, "read": stage_read,
         "sheets": stage_sheets, "index": stage_index, "source_map": stage_source_map, "takeoff": stage_takeoff,
         "reviews": stage_reviews, "match": stage_match, "vision": stage_vision, "floors": stage_floors,
         "schedules": stage_schedules}


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
