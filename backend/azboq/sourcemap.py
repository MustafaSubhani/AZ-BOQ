"""Source map: for every building and bill trade, which sheets can supply it and how much bill value sits there."""
from collections import defaultdict

from . import store

TRADE_DISCIPLINES = {
    "earthworks": ["structure", "architecture", "site"], "foundations": ["structure"],
    "reinforced_concrete": ["structure"], "walls": ["architecture", "structure"], "roof": ["architecture"],
    "doors_windows": ["architecture"], "floors": ["architecture"], "internal_finishes": ["architecture"],
    "external_finishes": ["architecture"], "finishes": ["architecture"], "water_sewer": ["water_sewer"],
    "heating": ["hvac", "site"], "ventilation": ["hvac"], "cooling": ["hvac"], "power": ["electrical"],
    "lighting": ["electrical"], "fire_alarm": ["low_current", "electrical"], "cctv": ["low_current", "electrical"],
    "communications": ["low_current", "electrical"], "technology": ["technology"], "gas": ["hvac", "site"],
    "automation": ["hvac", "electrical"], "demolition": ["site"], "grading": ["site"], "roads": ["site"],
    "pavements": ["site"], "landscaping": ["site"], "sand_pit": ["site", "structure"], "fence": ["structure", "site"],
    "seating": ["structure"], "misc": ["architecture", "structure"], "other": ["architecture", "structure", "site"],
}
BUILDING_ALIASES = {"fire_tank_3": "fire_tanks", "fire_tank_3a": "fire_tanks", "drinking_tank_5": "drinking_tanks",
                    "drinking_tank_5a": "drinking_tanks", "sand_pit": "sand_pit"}


def _sheet_sources():
    reg, sheets = store.get("register"), store.get("sheets")
    files = {f["sha256"]: f for f in reg["files"]}
    out = defaultdict(list)
    for sha, v in sheets["dwg"].items():
        f = files[sha]
        for r in v["regions"]:
            out[(r["building"], r["discipline"])].append(
                {"file": f["rel"], "file_id": sha, "kind": "dwg", "region": r["id"],
                 "sheet": (r["number"] or {}).get("raw"), "title": r["title"]})
    for sha, v in sheets["pdf"].items():
        f = files[sha]
        for pg in v["pages"]:
            out[(pg["building"], pg["discipline"])].append(
                {"file": f["rel"], "file_id": sha, "kind": "pdf", "page": pg["page"],
                 "sheet": (pg["number"] or {}).get("raw"), "title": pg["title"]})
    for f in reg["files"]:
        if f["kind"] in ("drawing_scan", "explanatory_note_scan", "estimate_scan"):
            out[(f.get("building"), f.get("discipline"))].append({"file": f["rel"], "file_id": f["sha256"], "kind": "scan"})
    return out


def build_source_map() -> dict:
    bill = store.get("bill")
    sources = _sheet_sources()
    cells = defaultdict(lambda: {"lines": 0, "value": 0.0})
    for line in bill["lines"]:
        b = BUILDING_ALIASES.get(line["building"], line["building"])
        c = cells[(b, line["trade"])]
        c["lines"] += 1
        c["value"] += line["amount"] or 0.0  # allow-default: money total, not a quantity
    rows = []
    for (building, trade), c in sorted(cells.items(), key=lambda kv: -kv[1]["value"]):
        found = []
        for disc in TRADE_DISCIPLINES.get(trade, []):
            found.extend(sources.get((building, disc), []))
        kinds = {s["kind"] for s in found}
        if "dwg" in kinds:
            status = "drawing"
        elif "pdf" in kinds:
            status = "pdf only"
        elif "scan" in kinds:
            status = "scan only"
        else:
            status = "nothing"
        rows.append({"building": building, "trade": trade, "lines": c["lines"], "value": round(c["value"], 2),
                     "status": status, "sources": found[:40], "source_count": len(found)})
    buildings = sorted({r["building"] for r in rows})
    trades = sorted({r["trade"] for r in rows})
    return {"cells": rows, "buildings": buildings, "trades": trades,
            "value_with_drawing": round(sum(r["value"] for r in rows if r["status"] == "drawing"), 2),
            "value_total": round(sum(r["value"] for r in rows), 2)}
