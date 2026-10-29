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

BUILDING_OK = {
    "depot": {"depot"}, "guard_room": {"guard_room"}, "tower": {"tower"}, "heating_point": {"heating_point"},
    "fire_tank_3": {"fire_tanks"}, "fire_tank_3a": {"fire_tanks"}, "drinking_tank_5": {"drinking_tanks"},
    "drinking_tank_5a": {"drinking_tanks"}, "pump_station": {"pump_station"}, "vehicle_wash": {"vehicle_wash"},
    "toilet": {"toilet"}, "gazebo": {"gazebo"}, "fence": {"fence"}, "generator": {"generator"},
    "site": {"site", "substation"},
}
STOP = {"olan", "ilə", "ile", "üçün", "ucun", "qədər", "qeder", "hazırlanması", "hazirlanmasi", "qurulması",
        "qurulmasi", "düzəldilməsi", "duzeldilmesi", "edilməsi", "edilmesi", "tipli", "qalınlığı", "qalinligi",
        "olduqda", "əlavə", "elave", "mm-ə", "sinifli", "üzrə", "uzre", "binaların", "binalarin", "tikinti"}
LEVEL_LIKE = re.compile(r"^[+\-±]")


def _decimals(q: float) -> int:
    s = f"{q:.6f}".rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def significant_digits(q: float) -> int:
    s = f"{abs(q):.6f}".rstrip("0").rstrip(".").replace(".", "").lstrip("0")
    return len(s)


def keywords(text: str) -> set[str]:
    words = {w for w in re.findall(r"[a-zəıöüşçğ]{4,}", fold_key(text))}
    return {w[:6] for w in words if w not in STOP}


class Finder:
    def __init__(self):
        idx = json.loads((config.CACHE_DIR / "number-index.json").read_text(encoding="utf-8"))
        self.by_value = defaultdict(list)
        self.by_region = defaultdict(list)
        for e in idx:
            if e["kind"] == "dxf_dim" or LEVEL_LIKE.match(e["token"].strip()):
                continue
            self.by_value[round(e["value"], 3)].append(e)
            if e["strength"] == "strong":
                self.by_region[(e["file_id"], e.get("region") or e.get("page"))].append(e)

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
            words = keywords(e["context"] + " " + (e.get("row_label") or ""))
            overlap = sorted(kw & words)
            sig = significant_digits(qty)
            unit_enough = e.get("unit") == unit and sig >= 3
            words_enough = len(overlap) >= (2 if sig < 3 else 1)
            if unit_enough or words_enough:
                strong.append({**e, "overlap": overlap})
            elif len(weak) < 5:
                weak.append({**e, "overlap": []})
        strong.sort(key=lambda e: (-len(e["overlap"]), e.get("unit") != unit))
        return strong, weak

    def pair(self, qty: float, regions: set, unit: str, description: str) -> list:
        """qty = a + b or a − b with a and b printed on one sheet already relevant to the section,
        each carrying the line's unit or a word of its description."""
        if significant_digits(qty) < 4:
            return []
        kw = keywords(description)
        tol = 10 ** -max(_decimals(qty), 1) / 2
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


def source_of(e: dict) -> dict:
    loc = {"kind": "pdf_span", "page": e.get("page"), "bbox": e.get("bbox")} if e["kind"] == "pdf_line" else \
        {"kind": "dxf_entity", "handle": e.get("handle"), "layer": e.get("layer"), "region": e.get("region"),
         "at": e.get("at")}
    return {"file_id": e["file_id"], "file_name": e["file"], "locator": loc, "raw_text": e["context"],
            "decoded_text": e["context"], "sheet": e.get("sheet"), "row_label": e.get("row_label"),
            "keywords": e.get("overlap")}
