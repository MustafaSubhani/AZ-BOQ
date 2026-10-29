"""Sheets inside drawings: model-space frames in DWG, pages in PDF, each classified by its title block.

One file can hold several buildings, and sheet numbers have typos (9336-04-MT,
9337-02-MH), so the number is parsed fuzzily and the stamp's building name wins.
"""
import re
from functools import lru_cache

import yaml

from . import config
from .text.normalise import fold_homoglyphs, fold_key

SHEET_NO = re.compile(r"\b(9\d{3})\s*-\s*(\d{1,2}[a-zA-Z]?(?:,\d{1,2}[a-z]?)?)\s*-\s*([A-ZƏİÜÖÇŞ]{1,4})\b")
PAPERS = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841),
          "A3x3": (891, 420), "A4x3": (630, 297), "A3x4": (1189, 420)}
INNER = {k: (w - 25, h - 10) for k, (w, h) in PAPERS.items()}
STAMP_WORDS = re.compile(r"(?i)vərəq|mərhələ|imza|format|tarix|dəyiş|sah\.?№|inv\.?\s*№|имза|ф[оo]рмат")
RATIO_TOL = 0.015


@lru_cache(maxsize=1)
def _marks() -> dict:
    return yaml.safe_load((config.RULES_DIR / "sheet_marks.yaml").read_text(encoding="utf-8"))


def parse_sheet_number(text: str) -> dict | None:
    m = SHEET_NO.search(fold_homoglyphs(text))
    if not m:
        return None
    order, mark, disc = m.group(1), m.group(2), m.group(3).upper()
    return {"raw": m.group(0), "order": order, "mark": mark, "discipline_mark": disc,
            "order_typo": order not in ("9335", "9526")}


def building_from_stamp(texts: list[str], include_depot: bool = False) -> str | None:
    """Specific building names first. Every title block repeats the project title
    '...4 çıxışlı Yanğınsöndürmə depo binasının tikintisi', so the depot word only
    counts when nothing more specific is named."""
    joined = fold_key(" ".join(texts))
    for row in _marks()["stamp_buildings"]:
        if row["building"] == "depot":
            continue
        if re.search(row["pattern"], joined):
            return row["building"]
    if include_depot:
        dep = next(r for r in _marks()["stamp_buildings"] if r["building"] == "depot")
        if re.search(dep["pattern"], joined):
            return "depot"
    return None


def classify_sheet(stamp_texts: list[str], file_building: str, file_discipline: str) -> dict:
    marks = _marks()
    number = None
    for t in stamp_texts:
        number = parse_sheet_number(t)
        if number:
            break
    stamp_b = building_from_stamp(stamp_texts)
    mark_b = marks["buildings_by_mark"].get(number["mark"]) if number else None
    disc = marks["disciplines_by_mark"].get(number["discipline_mark"]) if number else None
    depot_b = None if (stamp_b or mark_b) else building_from_stamp(stamp_texts, include_depot=True)
    if file_building not in ("depot", "site") and not stamp_b and not mark_b:
        depot_b = None
    building = stamp_b or mark_b or depot_b or file_building
    how = "stamp name" if stamp_b else ("sheet number" if mark_b else ("stamp name" if depot_b else "file name"))
    title = next((t for t in stamp_texts if TITLE_RE.search(t)), "")
    return {"number": number, "building": building, "building_from": how, "discipline": disc or file_discipline,
            "title": title[:120], "mismatch": bool(stamp_b and mark_b and stamp_b != mark_b)}


TITLE_RE = re.compile(r"(?i)planı|plan\b|kəsim|fasad|təsnif|eksplik|sxem|spesif|balans|səviyyəsində")


def region_title(texts_in_region: list[dict], fallback: str) -> str:
    """The sheet's drawing title: the largest text that reads like a title, else the stamp's."""
    cands = [t for t in texts_in_region if TITLE_RE.search(t["text"]) and len(t["text"]) < 160]
    if not cands:
        return fallback
    return max(cands, key=lambda t: (t["h"], -len(t["text"])))["text"].replace("\n", " ")[:120]


def _is_rect(pts) -> tuple | None:
    p = pts[:-1] if len(pts) == 5 and pts[0] == pts[-1] else pts
    if len(p) != 4:
        return None
    xs, ys = sorted({round(x, 1) for x, _ in p}), sorted({round(y, 1) for _, y in p})
    if len(xs) != 2 or len(ys) != 2:
        return None
    return xs[0], ys[0], xs[1], ys[1]


def _paper_match(w: float, h: float):
    if w <= 0 or h <= 0:
        return None
    long_, short = max(w, h), min(w, h)
    ratio = long_ / short
    for table, inner in ((PAPERS, False), (INNER, True)):
        for name, (pw, ph) in table.items():
            if abs(ratio - pw / ph) / (pw / ph) <= RATIO_TOL:
                return name, inner, long_ / pw
    return None


def detect_regions(dump: dict, file_building: str, file_discipline: str) -> list[dict]:
    texts = dump["texts"]
    cands = []
    for poly in dump["polys"]:
        if not poly["closed"] and not (len(poly["pts"]) == 5 and poly["pts"][0] == poly["pts"][-1]):
            continue
        rect = _is_rect(poly["pts"])
        if not rect:
            continue
        x0, y0, x1, y1 = rect
        pm = _paper_match(x1 - x0, y1 - y0)
        if not pm:
            continue
        cands.append({"bbox": rect, "paper": pm[0], "inner": pm[1], "scale": round(pm[2], 4), "handle": poly["handle"],
                      "layer": poly["layer"], "area": (x1 - x0) * (y1 - y0)})
    cands.sort(key=lambda c: c["area"])
    accepted = []

    def inside(t, b):
        return b[0] <= t["at"][0] <= b[2] and b[1] <= t["at"][1] <= b[3]

    for c in cands:
        b = c["bbox"]
        stamp = [t["text"] for t in texts if inside(t, b) and STAMP_WORDS.search(t["text"])]
        if len(stamp) < 2:
            continue
        if any(_overlap(b, a["bbox"]) > 0.7 for a in accepted):
            continue
        if sum(1 for a in accepted if _contains(b, a["bbox"])) >= 2:
            continue
        accepted.append(c)
    regions = []
    for i, c in enumerate(sorted(accepted, key=lambda c: (-c["bbox"][3], c["bbox"][0])), start=1):
        x0, y0, x1, y1 = c["bbox"]
        w, h = x1 - x0, y1 - y0
        stamp = [t["text"] for t in texts if inside(t, c["bbox"]) and t["at"][0] > x1 - 0.5 * w and t["at"][1] < y0 + 0.3 * h]
        info = classify_sheet(stamp, file_building, file_discipline)
        info["title"] = region_title([t for t in texts if inside(t, c["bbox"])], info["title"])
        regions.append({"id": f"R{i}", **c, **info, "method": "frame rectangle with stamp text",
                        "text_count": sum(1 for t in texts if inside(t, c["bbox"]))})
    regions.extend(_cluster_regions(texts, regions, file_building, file_discipline))
    if not regions:
        xs = [t["at"][0] for t in texts] or [0]
        ys = [t["at"][1] for t in texts] or [0]
        stamp = [t["text"] for t in texts if STAMP_WORDS.search(t["text"])][:40]
        info = classify_sheet(stamp + [t["text"] for t in texts[:400]], file_building, file_discipline)
        regions.append({"id": "R0", "bbox": (min(xs), min(ys), max(xs), max(ys)), "paper": None, "scale": None,
                        "method": "no frame found: whole drawing is one region", **info,
                        "text_count": len(texts)})
    return regions


def _cluster_regions(texts, regions, file_building, file_discipline) -> list[dict]:
    """Sheets without a recognisable frame: cluster leftover texts by distance and keep
    clusters that hold a title block."""
    def inside_any(t):
        return any(r["bbox"][0] <= t["at"][0] <= r["bbox"][2] and r["bbox"][1] <= t["at"][1] <= r["bbox"][3]
                   for r in regions)

    rest = [t for t in texts if not inside_any(t)]
    if len(rest) < 20:
        return []
    heights = sorted(t["h"] for t in rest if t["h"] > 0) or [1.0]
    step = heights[len(heights) // 2] * 40
    parent = list(range(len(rest)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid: dict = {}
    for i, t in enumerate(rest):
        grid.setdefault((int(t["at"][0] // step), int(t["at"][1] // step)), []).append(i)
    for (gx, gy), members in grid.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), []):
                    for i in members:
                        if i < j and abs(rest[i]["at"][0] - rest[j]["at"][0]) <= step and \
                                abs(rest[i]["at"][1] - rest[j]["at"][1]) <= step:
                            a, b = find(i), find(j)
                            if a != b:
                                parent[a] = b
    clusters: dict = {}
    for i in range(len(rest)):
        clusters.setdefault(find(i), []).append(rest[i])
    out = []
    n0 = len(regions)
    for members in sorted(clusters.values(), key=lambda m: (-max(t["at"][1] for t in m), min(t["at"][0] for t in m))):
        stamp_all = [t["text"] for t in members if STAMP_WORDS.search(t["text"])]
        if len(members) < 20 or len(stamp_all) < 2:
            continue
        xs, ys = [t["at"][0] for t in members], [t["at"][1] for t in members]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        w, h = x1 - x0, y1 - y0
        stamp = [t["text"] for t in members if t["at"][0] > x1 - 0.5 * w and t["at"][1] < y0 + 0.35 * h]
        info = classify_sheet(stamp + stamp_all, file_building, file_discipline)
        info["title"] = region_title(members, info["title"])
        out.append({"id": f"R{n0 + len(out) + 1}", "bbox": (x0, y0, x1, y1), "paper": None, "scale": None,
                    "inner": False, "handle": None, "layer": None, "area": w * h, **info,
                    "method": "text cluster with a title block (no frame rectangle found)", "text_count": len(members)})
    return out


def region_of(point, regions) -> str | None:
    for r in regions:
        b = r["bbox"]
        if b[0] <= point[0] <= b[2] and b[1] <= point[1] <= b[3]:
            return r["id"]
    return None


def _overlap(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / small if small else 0.0


def _contains(a, b) -> bool:
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]
