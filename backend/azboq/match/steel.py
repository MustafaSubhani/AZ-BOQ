"""Steel tables grouped by element family.

Each table names one mark and its kilograms. Those kilograms are not added into a
bill quantity unless the drawing also states how many of that mark are built.
Without that count the family stays blocked.
"""
import json
import re

from .. import config
from ..text.normalise import fold_key

_FAMILIES = (
    ("columns", "Columns", ("sutun",)),
    ("beams", "Beams", ("tir", "rigel")),
    ("slabs", "Slabs", ("ortuk", "tava")),
    ("belts", "Belts", ("kemer",)),
    ("stairs", "Stairs", ("pilleken",)),
    ("foundations", "Foundations", ("bunovre", "lentvari")),
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def steel_families(register: dict, bill: dict) -> list[dict]:
    marks: dict[str, list] = {key: [] for key, *_ in _FAMILIES}
    for path in (config.CACHE_DIR / "sheets").glob("*.schedules.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        file_name = data.get("file") or ""
        if not _depot_structure(register, data.get("sha256"), file_name):
            continue
        for table in data.get("tables") or []:
            if "polad" not in fold_key(table.get("title") or ""):
                continue
            for row in table.get("rows") or []:
                if row.get("section"):
                    continue
                cells = row.get("cells") or []
                if not cells:
                    continue
                mark = cells[0].get("text") or ""
                family = _family(mark)
                if family is None:
                    continue
                marks[family].append({
                    "mark": mark.strip(),
                    "a240_kg": _column(cells, "240", "cemi"),
                    "a500_kg": _column(cells, "a500", "cemi"),
                    "total_kg": _column(cells, "yekun"),
                    "file": file_name,
                    "handle": table.get("handle"),
                })
    pairs = _bill_pairs(bill)
    out = []
    for key, label, _words in _FAMILIES:
        rows = marks[key]
        out.append({
            "id": key,
            "label": label,
            "status": "blocked",
            "marks": len(rows),
            "tables": rows[:40],
            "bill_lines": pairs.get(key) or [],
            "reason": (
                f"{len(rows)} tables name one mark each and give kilograms for that mark. "
                "A count of how many of each mark are on the plan is not applied, so the kilograms are not added up "
                "and are not written onto the bill."
            ),
        })
    return [row for row in out if row["marks"] or row["bill_lines"]]


def _depot_structure(register: dict, sha: str | None, file_name: str) -> bool:
    for item in register.get("files") or []:
        if sha and item.get("sha256") == sha:
            return item.get("building") == "depot"
        if file_name and item.get("rel") == file_name:
            return item.get("building") == "depot"
    return False


def _family(mark: str) -> str | None:
    key = fold_key(mark)
    for family, _label, words in _FAMILIES:
        if any(word in key for word in words):
            return family
    return None


def _column(cells: list[dict], *needles: str | None) -> float | None:
    for cell in cells:
        header = fold_key(cell.get("header") or "")
        if not all(needle in header for needle in needles if needle):
            continue
        match = _NUMBER.fullmatch((cell.get("text") or "").strip().replace(" ", ""))
        if match:
            return float(match.group(0).replace(",", "."))
    return None


def _is_reinforcement(text: str) -> bool:
    key = fold_key(text)
    return "armatur" in key or re.search(r"\ba[\s-]*[13l]\b", key) is not None


def _bill_pairs(bill: dict) -> dict:
    """The tonne lines that follow a concrete line of the same family. Their quantities stay the bill's."""
    lines = bill.get("lines") or []
    found: dict[str, list] = {}
    for index, line in enumerate(lines):
        family = _family(line.get("description") or "")
        if family is None or line.get("unit") == "t":
            continue
        pair = []
        for nxt in lines[index + 1:index + 3]:
            if nxt.get("unit") != "t" or nxt.get("section") != line.get("section"):
                break
            if not _is_reinforcement(nxt.get("description") or ""):
                break
            pair.append({"id": nxt["id"], "qty": nxt.get("qty"), "unit": "t",
                         "description": nxt.get("description")})
        if pair:
            found.setdefault(family, []).extend(pair)
    return found
