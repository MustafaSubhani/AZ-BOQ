"""Evidence finder: is this bill quantity printed on a drawing of the same building?

A printed match needs all of: the same building, a strong number (four or more
digits, or a decimal) that is not a level mark or a signed value, and either the
bill's unit written next to the number or a word of the bill description in the
number's own text or row label. Anything weaker is at most a review candidate.
Sums and differences are only tried on sheets already proved relevant to the
bill section.
"""
import json
import re
from collections import defaultdict

from .. import config
from ..text.normalise import fold_key
from .elements import classify as element_of_text

BUILDING_OK = {
    "depot": {"depot"}, "guard_room": {"guard_room"}, "tower": {"tower"}, "heating_point": {"heating_point"},
    "fire_tank_3": {"fire_tanks"}, "fire_tank_3a": {"fire_tanks"}, "drinking_tank_5": {"drinking_tanks"},
    "drinking_tank_5a": {"drinking_tanks"}, "pump_station": {"pump_station"}, "vehicle_wash": {"vehicle_wash"},
    "toilet": {"toilet"}, "gazebo": {"gazebo"}, "fence": {"fence"}, "generator": {"generator"},
    "sand_pit": {"sand_pit"}, "site": {"site", "substation"},
}
STOP = {"olan", "ilə", "ile", "üçün", "ucun", "qədər", "qeder", "hazırlanması", "hazirlanmasi", "qurulması",
        "qurulmasi", "düzəldilməsi", "duzeldilmesi", "edilməsi", "edilmesi", "tipli", "qalınlığı", "qalinligi",
        "olduqda", "əlavə", "elave", "mm-ə", "sinifli", "üzrə", "uzre", "binaların", "binalarin", "tikinti"}
LEVEL_LIKE = re.compile(r"^[+\-±]")
SUBJECT = re.compile(r"(^|[^a-z])nov(?:lar\w*|un\w*)(?![a-z])")
# Azerbaijani written in Cyrillic (Новалчалар) is the same word as novalça.
_CYR_AZ = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ч": "c", "ш": "s",
    "ы": "i", "э": "e", "ю": "u", "я": "a", "ә": "e", "ө": "o", "ү": "u", "ғ": "g", "һ": "h",
})
ITEMISED = re.compile(r"h\s*=\s*(\d+(?:[.,]\d+)?)\s*p\.?m\.?\s*-\s*(\d+)")
ORDER_IN_SHEET = re.compile(r"9\d{3}")
THIS_PROJECT = {"9335", "9526"}


def owning_clause(entry: dict) -> str:
    """The dash-separated clause that contains this number, not the whole note.

    A roof note names gutters and downpipes in one paragraph. The length belongs
    to the clause that writes it: 'novun uzunluğu L=12.8', not the novalça clause after it.
    """
    text = entry.get("context") or ""
    token = str(entry.get("token") or "")
    alts = {token, token.replace(".", ",")}
    value = entry.get("value")
    if isinstance(value, (int, float)):
        alts.add(f"{value:g}")
        alts.add(f"{value:.1f}".rstrip("0").rstrip("."))
    for part in re.split(r"\s+-\s*|\n", text):
        if any(alt and alt in part for alt in alts):
            return part
    return text


def subject_class(text: str) -> str | None:
    """Gutter or downpipe, from the clause that owns the number. Novalça is not nov."""
    key = fold_key(text or "").translate(_CYR_AZ)
    if "novalca" in key or "axidici" in key:
        return "downpipe"
    if SUBJECT.search(key):
        return "gutter"
    return None


def file_problem(entry: dict) -> str | None:
    """A sheet of another order, or a drawing named as a second variant, is not this project's source."""
    sheet = entry.get("sheet") or ""
    orders = ORDER_IN_SHEET.findall(sheet)
    if orders and all(order not in THIS_PROJECT for order in orders):
        return f"sheet {sheet.strip()} belongs to order {orders[0]}, not this project"
    name = fold_key(entry.get("file") or "")
    if "2-ci variant" in name or "2 ci variant" in name:
        return "the file is named as a second variant"
    return None


def piece_total(entry: dict) -> tuple[float, int] | None:
    """'h=16.3 p.m. - 2 əd' is two pipes, so the length is 32.6 m, not 16.3."""
    match = ITEMISED.search(fold_key(entry.get("context") or ""))
    if not match:
        return None
    count = int(match.group(2))
    if count <= 1:
        return None
    each = float(match.group(1).replace(",", "."))
    return each * count, count


def _decimals(q: float) -> int:
    s = f"{q:.6f}".rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def _beside_level(entry: dict) -> bool:
    """A ± or a level mark sitting against the number is not a quantity."""
    token = entry.get("token") or ""
    if not token or "±" in token:
        return True
    ctx = entry.get("context") or ""
    if re.search(rf"[±]\s*{re.escape(token)}|{re.escape(token)}\s*[±]", ctx):
        return True
    return "seviyy" in fold_key(ctx) and bool(re.fullmatch(r"[+\-]?\d+(?:[.,]\d+)?", token))


COUNT_WORD = re.compile(r"(?<!\d)\d+\s*(?:əd\b|əd\.|ədəd)", re.I)
COUNT_COL = re.compile(r"(?i)say[ıi]|miqdar|ədəd|\bəd\b")


def count_hit_ok(entry: dict, line_element: str | None) -> bool:
    """A small each-count is printed only in a count column or as 'N ədəd' for the same element."""
    header = entry.get("col_header") or ""
    count_col = bool(COUNT_COL.search(header))
    if entry.get("schedule") and not count_col:
        return False
    if significant_digits(entry["value"]) >= 3 and not entry.get("schedule"):
        return True
    if count_col:
        return line_element is not None and element_of_text(entry.get("row_label") or "") == line_element
    if COUNT_WORD.search(entry.get("context") or ""):
        return line_element is not None and element_of_text(entry.get("context") or "") == line_element
    return False


def significant_digits(q: float) -> int:
    s = f"{abs(q):.6f}".rstrip("0").rstrip(".").replace(".", "").lstrip("0")
    return len(s)


def unit_carries(qty: float, entry: dict, unit: str) -> bool:
    """A schedule cell written with a decimal and a unit is an area, even when the bill prints 39."""
    sig = significant_digits(qty)
    token = entry.get("token") or ""
    schedule_area = bool(entry.get("schedule") and entry.get("unit") == unit and re.search(r"[.,]\d", token))
    return entry.get("unit") == unit and (sig >= 3 or schedule_area)


def keywords(text: str) -> set[str]:
    words = {w for w in re.findall(r"[a-zəıöüşçğ]{4,}", fold_key(text))}
    return {w[:6] for w in words if w not in STOP}


class Finder:
    def __init__(self):
        idx = json.loads((config.CACHE_DIR / "number-index.json").read_text(encoding="utf-8"))
        self.by_value = defaultdict(list)
        self.by_region = defaultdict(list)
        self.schedule = []
        self.by_subject = defaultdict(list)
        self.roof_windows = []
        for e in idx:
            if e.get("copy") or e["kind"] == "dxf_dim" or LEVEL_LIKE.match(e["token"].strip()):
                continue
            if e.get("schedule"):
                self.schedule.append(e)
            note = fold_key(e.get("context") or "")
            if e.get("unit") == "each" and "dam pencere" in note and "dp" in note:
                self.roof_windows.append(e)
            self.by_value[round(e["value"], 3)].append(e)
            if e["strength"] == "strong":
                self.by_region[(e["file_id"], e.get("region") or e.get("page"))].append(e)
                kind = subject_class(owning_clause(e))
                if kind and e.get("unit"):
                    self.by_subject[(e.get("building"), e.get("unit"), kind)].append(e)

    def roof_window(self, building: str) -> dict | None:
        """The ədəd count in 'Dam pəncərəsi DP-1 (N əd)' when the building states one count."""
        seen = set()
        hits = []
        for e in self.roof_windows:
            if e.get("building") != building:
                continue
            key = (e.get("context"), e["value"])
            if key in seen:
                continue
            seen.add(key)
            hits.append(e)
        if len({e["value"] for e in hits}) != 1:
            return None
        return hits[0]

    def direct(self, qty: float, unit: str, building: str, description: str) -> tuple[list, list]:
        ok_b = BUILDING_OK.get(building, {building})
        kw = keywords(description)
        strong, weak = [], []
        for e in self.by_value.get(round(qty, 3), []):
            if e.get("building") not in ok_b:
                continue
            if e.get("unit") not in (None, unit):
                continue
            if e["strength"] != "strong":
                continue
            # Three decimals and a value under 100 reads as a level mark unless the line is a volume or tonnage.
            if re.fullmatch(r"\d{1,2}[.,]\d{3}", e["token"]) and unit not in ("m³", "t"):
                continue
            if _beside_level(e):
                continue
            problem = file_problem(e)
            if problem:
                if len(weak) < 5:
                    weak.append({**e, "overlap": [], "problem": problem})
                continue
            length_note = length_problem(e, description) if unit == "m" else None
            if length_note is None and unit in ("m²", "m³"):
                length_note = named_area_problem(e, description)
            # A gutter line must still see the downpipe sentence, so the swap can name both.
            if unit == "m" and length_note == "the sentence names a different thing" and subject_class(description):
                length_note = None
            if length_note:
                if len(weak) < 5:
                    weak.append({**e, "overlap": [], "problem": length_note})
                continue
            if unit == "each" and not count_hit_ok(e, element_of_text(description)):
                if len(weak) < 5:
                    weak.append({**e, "overlap": []})
                continue
            words = keywords(e["context"] + " " + (e.get("row_label") or ""))
            overlap = sorted(kw & words)
            sig = significant_digits(qty)
            unit_enough = unit_carries(qty, e, unit)
            words_enough = len(overlap) >= (2 if sig < 3 else 1)
            if unit_enough or words_enough:
                strong.append({**e, "overlap": overlap})
            elif len(weak) < 5:
                weak.append({**e, "overlap": []})
        strong.sort(key=lambda e: (-len(e["overlap"]), e.get("unit") != unit))
        return strong, weak

    def for_subject(self, building: str, unit: str, kind: str) -> list[dict]:
        ok_b = BUILDING_OK.get(building, {building})
        return [e for (b, u, k), rows in self.by_subject.items() if k == kind and u == unit and b in ok_b for e in rows]

    def note_conflicts(self) -> list[dict]:
        """A stated total that does not equal the itemised lines printed next to it."""
        stated = None
        parts = []
        seen = set()
        for rows in self.by_value.values():
            for e in rows:
                if e.get("building") != "depot":
                    continue
                ctx = e.get("context") or ""
                if ctx in seen:
                    continue
                key = fold_key(ctx)
                if "novalca" not in key:
                    continue
                seen.add(ctx)
                if e.get("unit") == "m" and re.search(r"l\s*=", key):
                    stated = e
                    continue
                m = ITEMISED.search(key)
                if m:
                    parts.append((float(m.group(1).replace(",", ".")), int(m.group(2))))
        if stated is None or len(parts) < 2:
            return []
        total = round(sum(n * c for n, c in parts), 4)
        if abs(total - stated["value"]) <= 0.05:
            return []
        return [{"id": "downpipes", "stated": stated["value"], "itemised": total,
                 "parts": [f"{c} × {n:g}" for n, c in parts],
                 "text": f"downpipes: stated {stated['value']:g} m, itemised {total:g} m"}]

    def near_schedule(self, qty: float, unit: str, building: str, description: str) -> dict | None:
        """One schedule figure of the same unit, close to the bill quantity but not equal to it."""
        if unit not in ("m²", "m³"):
            return None
        ok_b = BUILDING_OK.get(building, {building})
        kw = keywords(description)
        hits = []
        for e in self.schedule:
            if e.get("building") not in ok_b or e.get("unit") != unit or not e.get("value"):
                continue
            gap = abs(qty - e["value"])
            if gap <= 0.5 * 10 ** -_decimals(qty) + 1e-6:
                continue
            close = gap / abs(e["value"])
            words = keywords(e.get("context") or "") | keywords(e.get("row_label") or "")
            shared = kw & words
            # A nearby schedule figure counts only when the row says the same thing as the bill line.
            if shared and close <= 0.08:
                hits.append((len(shared), e))
        if not hits:
            return None
        best = max(n for n, _ in hits)
        kept = [e for n, e in hits if n == best]
        values = {round(h["value"], 4) for h in kept}
        if len(values) != 1:
            return None
        return kept[0]

    def pair(self, qty: float, regions: set, unit: str, description: str) -> list:
        """qty = a + b or a − b with a and b printed on one sheet already relevant to the section,
        each carrying the line's unit or a word of its description."""
        if significant_digits(qty) < 4:
            return []
        kw = keywords(description)
        tol = 10 ** -max(_decimals(qty), 1) / 2  # allow-default: pair search tolerance, not a quantity
        for key in regions:
            usable = [e for e in self.by_region.get(key, []) if e.get("unit") == unit or
                      kw & keywords(e["context"] + " " + (e.get("row_label") or "")) or
                      re.fullmatch(r"[\d.,\s]+", e["context"].strip())]
            vals = sorted({round(e["value"], 3): e for e in usable}.items())
            if len(vals) > 600:
                continue
            for i, (a, ea) in enumerate(vals):
                for b, eb in vals[i + 1:]:
                    if abs(a + b - qty) <= tol:
                        return [{"op": "+", "a": ea, "b": eb}]
                    if abs(b - a - qty) <= tol:
                        return [{"op": "−", "a": eb, "b": ea}]
        return []


def size_tokens(text: str) -> set[str]:
    """Diameters and cable sections, so '3x4' and '3х4' are the same size."""
    key = fold_key(text or "").translate(_CYR_AZ).replace("×", "x").replace("х", "x")
    found = {f"{a}x{b}" for a, b in re.findall(r"(\d+)\s*x\s*(\d+)", key)}
    found.update(f"d{n}" for n in re.findall(r"(?:diametr\w*|d)\s*[=:]?\s*(\d+)", key))
    found.update(f"d{n}" for n in re.findall(r"(\d+)\s*mm", key))
    return found


def length_problem(entry: dict, description: str) -> str | None:
    """A length written in a gutter or downpipe clause cannot confirm a different line.

    A bare number with no unit, or a number whose row does not name this line, is not a length either.
    """
    clause = owning_clause(entry)
    drawn = subject_class(clause)
    billed = subject_class(description)
    if drawn and drawn != billed:
        return "the sentence names a different thing"
    blob = clause + " " + (entry.get("row_label") or "")
    named = bool(keywords(blob) & keywords(description)) or bool(size_tokens(blob) & size_tokens(description))
    if entry.get("unit") == "m":
        if drawn or named:
            return None
        return "the number is written with a unit but the row does not name this line"
    if len(keywords(clause) & keywords(description)) < 2:
        return "the number has no unit and only one nearby word"
    return None


def _words_before_number(entry: dict) -> str:
    """The subject is what is written before the number, not the next sentence."""
    text = entry.get("context") or ""
    token = str(entry.get("token") or "")
    at = text.find(token)
    if at < 0:
        at = text.find(token.replace(".", ","))
    if at < 0:
        return ""
    start = at - 48
    if start < 0:
        start = 0
    return text[start:at]


def named_area_problem(entry: dict, description: str) -> str | None:
    """An area written next to a different subject cannot confirm this line.

    'Yolların sahəsi — 216 m²' is the road. It is not an extra 3 cm of pavement.
    A bare cell, a 'Cəmi' total, or words the bill line also uses, still counts.
    """
    if entry.get("schedule"):
        return None
    phrase = _words_before_number(entry)
    blob = phrase + " " + (entry.get("row_label") or "")
    if keywords(blob) & keywords(description):
        return None
    if size_tokens(blob) & size_tokens(description):
        return None
    words = keywords(phrase)
    if not words or words <= {"cemi", "umumi"}:
        return None
    return "the sentence names a different thing"


def source_of(e: dict) -> dict:
    at = e.get("at")
    if e.get("kind") == "dxf_text" and e.get("handle") and e.get("token") and e.get("file_id"):
        from ..engine.locate import focus_handle
        focused = focus_handle(e["file_id"], e["handle"], str(e["token"]), e.get("at"))
        if focused:
            at = focused
    loc = {"kind": "pdf_span", "page": e.get("page"), "bbox": e.get("bbox")} if e["kind"] == "pdf_line" else \
        {"kind": "dxf_entity", "handle": e.get("handle"), "layer": e.get("layer"), "region": e.get("region"),
         "at": at}
    out = {"file_id": e["file_id"], "file_name": e["file"], "locator": loc, "raw_text": e["context"],
            "decoded_text": e["context"], "sheet": e.get("sheet"), "row_label": e.get("row_label"),
            "keywords": e.get("overlap")}
    if e.get("problem"):
        out["problem"] = e["problem"]
    return out
