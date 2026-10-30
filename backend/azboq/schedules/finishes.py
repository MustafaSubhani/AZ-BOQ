"""Finish-schedule areas. Each m² cell keeps the description printed beside it.

A ceiling that says alçıpan is plasterboard even when the same sentence also says
metal or emulsion. Whitewash is the əhəng row, not every plastered wall.
"""
import re

from ..text.normalise import fold_key
from ..values import Method, Source, Status, Value, blocked, derive

_CYR = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "u", "ч": "c", "ш": "s", "щ": "s",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "u", "я": "e",
    "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ё": "e", "Ж": "j", "З": "z",
    "И": "i", "Й": "y", "К": "k", "Л": "l", "М": "m", "Н": "n", "О": "o", "П": "p", "Р": "r",
    "С": "s", "Т": "t", "У": "u", "Ф": "f", "Х": "x", "Ц": "u", "Ч": "c", "Ш": "s", "Щ": "s",
    "Ъ": "", "Ы": "i", "Ь": "", "Э": "e", "Ю": "u", "Я": "e",
})


def _key(text: str) -> str:
    return fold_key((text or "").translate(_CYR))


def finish_kind(side: str, description: str) -> str | None:
    key = _key(description)
    if side == "ceiling":
        if "alcipan" in key:
            return "plasterboard"
        if "metal" in key:
            return "metal"
        if "eheng" in key or "agard" in key:
            return "whitewash"
        if "emulsi" in key or "hamarl" in key:
            return "paint"
        return None
    if "keramik" in key or "tavala" in key:
        return "ceramic"
    if "eheng" in key or "agard" in key:
        return "whitewash"
    if "emulsi" in key or "suvan" in key or "hamarl" in key:
        return "plaster"
    return None


def _finish_table(table: dict) -> bool:
    blob = _key(table.get("title", "") + " " + " ".join(c.get("header") or "" for c in table.get("columns") or []))
    return "bezek" in blob or ("tavan" in blob and "divar" in blob)


def _side(desc: dict, area: dict) -> str | None:
    header = _key(desc.get("header") or "")
    if "tavan" in header:
        return "ceiling"
    if "divar" in header:
        return "wall"
    area_header = _key(area.get("header") or "")
    if "interyer" in area_header or "tavan" in area_header:
        return "ceiling"
    if "sahe" in area_header:
        return "wall"
    return None


def finish_areas(tables: list[dict]) -> list[dict]:
    found = []
    for table in tables:
        if not _finish_table(table):
            continue
        for row in table.get("rows") or []:
            if row.get("section"):
                continue
            desc = None
            for cell in row.get("cells") or []:
                text = (cell.get("text") or "").strip()
                if cell.get("unit") == "m²" and re.fullmatch(r"\d+(?:[.,]\d+)?", text):
                    if desc is None:
                        continue
                    side = _side(desc, cell)
                    kind = finish_kind(side, desc["text"]) if side else None
                    if side and kind and row.get("floor"):
                        found.append({
                            "floor": row["floor"], "side": side, "kind": kind, "page": table.get("page"),
                            "value": float(text.replace(",", ".")), "cell": cell, "description": desc["text"],
                        })
                    desc = None
                    continue
                if text and not re.fullmatch(r"[\d\s.*]+", text):
                    desc = cell
    return found


def _cell_value(sha: str, file_name: str, page, cell: dict, number: float) -> Value:
    src = Source(sha, file_name, {"kind": "pdf_span", "page": page, "bbox": cell.get("bbox")},
                 cell.get("text"), cell.get("text"))
    return Value(float(number), "m²", Method.SCHEDULE, Status.EXTRACTED, sources=(src,))


def finish_sum(areas: list[dict], rule: dict, sha: str, file_name: str) -> Value:
    """Sum the finish cells of one side and kind. Every cell stays an input."""
    floors = set(rule.get("floors") or [])
    chosen = [a for a in areas if a["side"] == rule["side"] and a["kind"] == rule["kind"]
              and (not floors or a["floor"] in floors)]
    if not chosen:
        return blocked(rule["unit"], [rule["id"]], [file_name],
                       f"no {rule['side']} {rule['kind']} cells", Method.SCHEDULE)
    inputs = {f"a{i}": _cell_value(sha, file_name, a["page"], a["cell"], a["value"])
              for i, a in enumerate(chosen, 1)}
    formula = " + ".join(inputs)
    return derive(rule["unit"], formula, lambda **kw: sum(kw.values()), **inputs)
