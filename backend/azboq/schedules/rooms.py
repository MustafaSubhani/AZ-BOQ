"""Room schedules printed on the floor plans.

Each plan lists a room number, a name and an area, then a Cəmi. The columns are
read by their position. The sum of the rooms is compared with the printed Cəmi.
"""
import re

import pymupdf

from ..floors import classify
from ..text.normalise import fold_key
from .tables import _page_lines

_NUM = re.compile(r"^\d{1,2}\*?$")
_AREA = re.compile(r"^\d+(?:[.,]\d+)$")


def _page_floor(lines: list[dict]) -> str | None:
    titled = [(i, ln) for i, ln in enumerate(lines) if "plani" in fold_key(ln["text"])]
    titled.sort(key=lambda item: item[1]["bbox"][1], reverse=True)
    for i, ln in titled:
        blob = ln["text"] if i == 0 else lines[i - 1]["text"] + " " + ln["text"]
        floor = classify(blob) or classify(ln["text"])
        if floor:
            return floor
    return None


def _take(lines, y, lo, hi, used):
    best = None
    for i, ln in enumerate(lines):
        if i in used:
            continue
        x = ln["bbox"][0]
        if not (lo <= x <= hi):
            continue
        dy = abs(ln["bbox"][1] - y)
        if dy > 6:
            continue
        if best is None or dy < best[0]:
            best = (dy, i, ln)
    if best is None:
        return None
    used.add(best[1])
    return best[2]


def rooms_on_page(page, page_no: int) -> dict | None:
    lines = _page_lines(page)
    floor = _page_floor(lines)
    if floor is None:
        return None
    areas = [ln for ln in lines if ln["bbox"][0] > 1080 and _AREA.match(ln["text"].replace(" ", ""))]
    numbers = [ln for ln in lines if 900 <= ln["bbox"][0] <= 950 and _NUM.match(ln["text"].replace(" ", ""))]
    if len(areas) < 3 or not numbers:
        return None
    cemi_lines = [ln for ln in lines if fold_key(ln["text"]) == "cemi" and 900 <= ln["bbox"][0] <= 1100]
    total = None
    total_line = None
    used_areas = set()
    if cemi_lines:
        cemi = max(cemi_lines, key=lambda ln: ln["bbox"][1])
        total_line = _take(areas, cemi["bbox"][1], 1080, 1300, used_areas)
        if total_line:
            total = float(total_line["text"].replace(",", "."))
    rows = []
    used_names = set()
    for num in numbers:
        area = _take(areas, num["bbox"][1], 1080, 1300, used_areas)
        name = _take(lines, num["bbox"][1], 945, 1100, used_names)
        if area is None:
            continue
        if name and fold_key(name["text"]) == "cemi":
            continue
        rows.append({
            "room": num["text"].replace("*", ""),
            "name": name["text"] if name else "",
            "area": float(area["text"].replace(",", ".")),
            "text": area["text"].strip(),
            "bbox": area["bbox"],
        })
    if not rows:
        return None
    summed = round(sum(row["area"] for row in rows), 2)
    return {"page": page_no, "floor": floor, "rows": rows, "total": total,
            "total_text": total_line["text"].strip() if total_line else None,
            "sum": summed,
            "gap": None if total is None else round(total - summed, 2)}


def read_rooms(path, pages: list[int] | None = None) -> list[dict]:
    doc = pymupdf.open(path)
    chosen = pages if pages is not None else range(len(doc))
    out = []
    for i in chosen:
        found = rooms_on_page(doc[i], i)
        if found:
            out.append(found)
    return out
