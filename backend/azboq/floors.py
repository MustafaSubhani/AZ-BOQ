"""Storey named on a bill line or a sheet title.

A floor is recorded only when the text says it (zirzəmi, 1-ci mərtəbə, dam örtüyü).
A line that does not say is left unstated. Nothing is inferred from the trade.
"""
import re
from collections import Counter, defaultdict

from . import store
from .groups import buildup_groups
from .text.normalise import fold_key

# Order is the order of the grouped bill. Patterns run on the fold key.
FLOORS = (
    ("basement", re.compile(r"zirzemi|texniki\s+doseme"), "Zirzəmi", "Basement"),
    ("floor_2", re.compile(r"2\s*[-.]?\s*ci\s+mert|(?<![a-z])ii\s+mert|ikinci\s+mert"), "2-ci mərtəbə", "2nd floor"),
    ("floor_1", re.compile(r"1\s*[-.]?\s*ci\s+mert|(?<![a-z])i\s+mert|birinci\s+mert"), "1-ci mərtəbə", "1st floor"),
    ("floor_3", re.compile(r"3\s*[-.]?\s*c[iu]\s+mert"), "3-cü mərtəbə", "3rd floor"),
    ("roof", re.compile(r"dam\s+ortuy|dam\s+plani"), "Dam", "Roof"),
)
BY_ID = {f[0]: f for f in FLOORS}
UNSTATED = "unstated"


def classify(text: str | None) -> str | None:
    if not text:
        return None
    key = fold_key(text)
    for fid, pat, _az, _en in FLOORS:
        if pat.search(key):
            return fid
    return None


def label(floor_id: str) -> tuple[str, str]:
    if floor_id == UNSTATED:
        return "Mərtəbə yazılmayıb", "Floor not stated"
    row = BY_ID.get(floor_id)
    return (row[2], row[3]) if row else (floor_id, floor_id)


def _line_floor(line: dict, section_title: str) -> dict:
    on_line = classify(line.get("description"))
    if on_line:
        return {"floor": on_line, "from": "line"}
    on_section = classify(section_title)
    if on_section:
        return {"floor": on_section, "from": "section"}
    return {"floor": UNSTATED, "from": None}


def build_floors() -> dict:
    bill = store.get("bill")
    sheets = store.get("sheets") or {"dwg": {}, "pdf": {}}
    titles = {s["code"]: s["title"] for s in bill["sections"]}
    lines = {}
    for line in bill["lines"]:
        lines[line["id"]] = _line_floor(line, titles.get(line["section"], ""))
    from . import runlog
    for group in buildup_groups(bill["lines"]):
        named = {classify(line.get("description")) for line in group["lines"]}
        named.discard(None)
        if len(named) > 1:
            ids = ", ".join(line["id"] for line in group["lines"][:4])
            runlog.warn("floors", f"build-up {ids} names more than one floor: {', '.join(sorted(named))}")
            continue
        if len(named) != 1:
            continue
        floor = next(iter(named))
        for line in group["lines"]:
            rec = lines[line["id"]]
            if rec["floor"] == UNSTATED:
                rec["floor"] = floor
                rec["from"] = "group"
    regions = []
    for sha, info in sheets["dwg"].items():
        for region in info["regions"]:
            floor = classify(region.get("title"))
            if not floor:
                continue
            number = region.get("number") or {}
            regions.append({"file": info["file"], "file_id": sha, "kind": "dwg", "region": region["id"],
                            "sheet": number.get("raw") if isinstance(number, dict) else number,
                            "title": region.get("title"), "building": region.get("building"), "floor": floor})
    for sha, info in sheets["pdf"].items():
        for page in info["pages"]:
            floor = classify(page.get("title"))
            if not floor:
                continue
            number = page.get("number") or {}
            regions.append({"file": info["file"], "file_id": sha, "kind": "pdf", "page": page.get("page"),
                            "sheet": number.get("raw") if isinstance(number, dict) else number,
                            "title": page.get("title"), "building": page.get("building"), "floor": floor})
    counts = Counter(v["floor"] for v in lines.values())
    by_floor = defaultdict(list)
    for region in regions:
        by_floor[region["floor"]].append(region)
    return {
        "lines": lines,
        "counts": dict(counts),
        "sheet_counts": {k: len(v) for k, v in by_floor.items()},
        "sheets": regions,
        "order": [f[0] for f in FLOORS] + [UNSTATED],
    }
