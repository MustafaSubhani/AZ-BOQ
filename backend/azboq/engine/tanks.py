"""Concrete rows in a tank material table.

`Beton "B 25"` is the same row as `Beton "B25"`. A table that says `1 ədəd üçün`
is one wall. The wall count is the Md-1 marks on one plan; marks in several
places are not a count, and 4 is never assumed because the bill would fit.
"""
import re
from collections import defaultdict

from ..text.normalise import fold_key
from . import locate as L

_CELL = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(m³|m3)\s*$", re.I)
_TITLE_REACH = 12000


def _is_b25(text: str) -> bool:
    compact = fold_key(text).replace(" ", "").replace('"', "")
    return "beton" in compact and "b25" in compact and "b10" not in compact and len(fold_key(text).split()) <= 6


def _role(title: str) -> str | None:
    key = fold_key(title)
    if "ortuk" in key:
        return "cover"
    if "bunovr" in key:
        return "bottom"
    if "divar" in key:
        return "wall"
    return None


def _nearest_title(anchor, texts) -> dict | None:
    y = anchor["at"][1]
    best = None
    for t in texts:
        key = fold_key(t["text"])
        if "material" not in key or "serf" not in key:
            continue
        dy = abs(t["at"][1] - y)
        if dy > _TITLE_REACH:
            continue
        if best is None or dy < best[0]:
            best = (dy, t)
    return best[1] if best else None


def _per_element(anchor, texts) -> bool:
    y = anchor["at"][1]
    for t in texts:
        if abs(t["at"][1] - y) > _TITLE_REACH:
            continue
        key = fold_key(t["text"])
        if "eded ucun" in key or "1 eded" in key:
            return True
    return False


def _volume(anchor, texts) -> dict | None:
    reach = anchor["h"] * 60 if anchor.get("h") else None
    for other in L.row_of(anchor, texts, max_dx=reach):
        if other is anchor:
            continue
        m = _CELL.match((other.get("text") or "").replace("\n", " "))
        if m:
            return {"value": float(m.group(1).replace(",", ".")), "text": other}
    return None


def _spec_count(texts: list[dict]) -> dict | None:
    """The integer in the Miq. column of the row named Monolit divar."""
    names = [t for t in texts if fold_key(t.get("text") or "").strip() == "monolit divar"]
    if len(names) != 1:
        return None
    name = names[0]
    headers = [t for t in texts if fold_key(t.get("text") or "").strip().rstrip(".") == "miq"
               and t["at"][1] >= name["at"][1] and t["at"][1] - name["at"][1] < 8000]
    if not headers:
        return None
    header = min(headers, key=lambda t: t["at"][1] - name["at"][1])
    reach = header.get("h")
    if not reach:
        return None
    nxt = [t for t in texts if abs(t["at"][1] - header["at"][1]) <= reach and t["at"][0] > header["at"][0] + 50]
    nxt.sort(key=lambda t: t["at"][0])
    if not nxt:
        return None
    x1 = nxt[0]["at"][0]
    qty = []
    for t in texts:
        if not re.fullmatch(r"\d{1,2}", (t.get("text") or "").strip()):
            continue
        if not (header["at"][0] - 100 <= t["at"][0] < x1):
            continue
        limit = name.get("h")
        other = t.get("h")
        if other and (limit is None or other > limit):
            limit = other
        if limit and abs(t["at"][1] - name["at"][1]) <= limit:
            qty.append(t)
    if len(qty) != 1:
        return None
    return {"n": int(qty[0]["text"]), "marks": [qty[0], name], "header": header}


def _wall_check(texts, wall_m3: float | None) -> str:
    """One wall's printed area times the stated thickness, compared with the material-table volume."""
    thick = []
    for t in texts:
        key = fold_key(t.get("text") or "")
        if "divar" not in key or "mm" not in key or "dib" in key or "ortuk" in key:
            continue
        m = re.search(r"(\d+)\s*mm", key)
        if m:
            thick.append(int(m.group(1)))
    if len(set(thick)) != 1 or wall_m3 is None:
        return ""
    mm = thick[0]
    areas = []
    names = [t for t in texts if fold_key(t.get("text") or "").strip() == "monolit divar"]
    if len(names) != 1:
        return ""
    name = names[0]
    for t in texts:
        m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*m²\s*", (t.get("text") or "").replace("\n", " "))
        if not m:
            continue
        limit = name.get("h")
        other = t.get("h")
        if other and (limit is None or other > limit):
            limit = other
        if limit and abs(t["at"][1] - name["at"][1]) <= limit:
            areas.append(float(m.group(1).replace(",", ".")))
    if len(areas) != 1:
        return ""
    got = areas[0] * mm / 1000
    if abs(got - wall_m3) > 0.05 * wall_m3:
        return f"row area {areas[0]:g} m² × {mm} mm = {got:.3f} m³, the material table gives {wall_m3:g} m³"
    return f"row area {areas[0]:g} m² × {mm} mm agrees with {wall_m3:g} m³"


def _mark_clusters(texts) -> list[list[dict]]:
    marks = [t for t in texts if fold_key(t.get("text") or "").strip() == "md-1"]
    clusters: list[list[dict]] = []
    for t in sorted(marks, key=lambda item: item["at"][1]):
        height = t.get("h")
        close = clusters and height and abs(t["at"][1] - clusters[-1][-1]["at"][1]) <= height * 8
        if close:
            clusters[-1].append(t)
        else:
            clusters.append([t])
    return clusters


def read_tank(sha: str, building: str) -> dict:
    texts = [t for t, _ in L.texts_in(sha, building)]
    found = defaultdict(list)
    dropped = []
    for anchor, region in L.texts_in(sha, building):
        if not _is_b25(anchor["text"]):
            continue
        volume = _volume(anchor, texts)
        title = _nearest_title(anchor, texts)
        if volume is None or title is None or _role(title["text"]) is None:
            dropped.append({"anchor": anchor["text"], "region": (region or {}).get("id"),
                            "why": "no m³ in the row" if volume is None else "no material-table title"})
            continue
        role = _role(title["text"])
        found[role].append({
            "role": role, "value": volume["value"], "per_element": _per_element(anchor, texts) if role == "wall" else False,
            "title": title["text"].replace("\n", " "), "anchor": anchor, "value_text": volume["text"], "region": region,
        })
    rows = {}
    for role, group in found.items():
        values = {round(row["value"], 4) for row in group}
        row = group[0]
        row["conflict"] = len(values) > 1
        rows[role] = row
    spec = _spec_count(texts)
    wall_m3 = (rows.get("wall") or {}).get("value")
    check = _wall_check(texts, wall_m3)
    if spec:
        note = f"the Miq. column prints {spec['n']} on the Monolit divar row"
        if check:
            note += "; " + check
        count = {"n": spec["n"], "marks": spec["marks"]}
    else:
        clusters = _mark_clusters(texts)
        count = None
        if len(clusters) == 1:
            count = {"n": len(clusters[0]), "marks": clusters[0]}
            note = f"{count['n']} Md-1 marks on one plan"
        elif clusters:
            note = "Md-1 marks are not in one place, and the sheet does not state how many walls"
        else:
            note = "no Md-1 mark on the plan"
        if check.startswith("row area") and "agrees" not in check:
            note += "; " + check
    return {"rows": rows, "count": count, "count_note": note, "dropped": dropped}
