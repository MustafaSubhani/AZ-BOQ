"""Read BOQ-Hadrut.xlsx.

Every data cell in columns A–E is a formula into a workbook that is not in the
package ([6] = Hadrut Smeta(AutoRecovered).xlsx000.xlsx). The cached values are
the only data, so the workbook is read twice (values and formulas) and never saved.
"""
import re
from collections import defaultdict

import openpyxl

from .. import config, runlog
from ..text.normalise import canonical_unit, fold_key

FIRST_DATA_ROW = 10
TOTALS = {"temporary": 2331, "contingency": 2332, "subtotal": 2333, "vat": 2334, "total": 2335}
_HEADER_CODE = re.compile(r"^\s*\d+(?:[.,]\d+)+\s*$")
_MARK = re.compile(r"(?:İ|I)D\s*[-–]?\s*(\d+)", re.IGNORECASE)

TRADES = [
    (r"torpaq", "earthworks"), (r"bunovre", "foundations"), (r"d/b|konst|kostr|karkas", "reinforced_concrete"),
    (r"divar", "walls"), (r"dam ortuy|ortuk", "roof"), (r"qapi|pencere", "doors_windows"), (r"doseme", "floors"),
    (r"daxili bezek", "internal_finishes"), (r"xarici bezek", "external_finishes"), (r"bezek", "finishes"),
    (r"kanalizasiya|su kemeri|su sebeke|boru", "water_sewer"), (r"isitme|istilik sebeke", "heating"),
    (r"ventilyasiya", "ventilation"), (r"kondision", "cooling"), (r"guc", "power"),
    (r"isiqlan|isqilan", "lighting"), (r"siqnalizasiya", "fire_alarm"), (r"videomusahide", "cctv"),
    (r"rabite|anons|telefon|televiziya|seslendirme", "communications"), (r"texnolo", "technology"),
    (r"qaz", "gas"), (r"avtomatika", "automation"), (r"soku", "demolition"), (r"saquli", "grading"),
    (r"yol", "roads"), (r"seki|meydanc", "pavements"), (r"yasillas", "landscaping"), (r"qum", "sand_pit"),
    (r"hasar|istinad", "fence"), (r"oturacaq", "seating"), (r"0,4 kv|generator", "power"),
    (r"artirma|cala|pilleken|muxtelif", "misc"),
]

BUILDING_BY_SECTION_PREFIX = [
    (r"qum meydan", "sand_pit"),
    (r"yangin deposu", "depot"), (r"nezaretci", "guard_room"), (r"qulle", "tower"), (r"istilik", "heating_point"),
    (r"81 m3.*1-ci", "fire_tank_3"), (r"81 m3.*2-ci", "fire_tank_3a"), (r"27 m3.*1-ci", "drinking_tank_5"),
    (r"27 m3.*2-ci", "drinking_tank_5a"), (r"nasos", "pump_station"), (r"avtoyuma", "vehicle_wash"),
    (r"ayaqyolu", "toilet"), (r"sohbetgah", "gazebo"), (r"istinad|hasar", "fence"), (r"generator", "generator"),
]


def _trade(title: str) -> str:
    inner = re.findall(r"\(([^()]*)\)?", title)
    text = fold_key(" ".join(inner) if inner else title)
    return next((t for pat, t in TRADES if re.search(pat, text)), "other")


def _named_building(title: str) -> str | None:
    """The building the title itself names. None when the title only names a trade."""
    key = fold_key(title)
    for pat, b in BUILDING_BY_SECTION_PREFIX:
        if re.search(pat, key):
            return b
    return None


def _mark(title: str) -> str | None:
    m = _MARK.search(title or "")
    return f"İD-{int(m.group(1))}" if m else None


def _header_parts(a) -> list[str] | None:
    """A section code in column A: a float such as 2.1, or a string such as '25,1,1'."""
    if isinstance(a, bool) or a in (None, ""):
        return None
    if isinstance(a, float):
        if a == 0:
            return None
        # 2.1 is one decimal; 2.10 cannot be told from 2.1, so the integer sequence repairs it later.
        return None
    if isinstance(a, str) and _HEADER_CODE.match(a):
        return [str(int(p)) for p in re.split(r"[.,]", a.strip())]
    return None


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse_bill(path=config.BILL_PATH) -> dict:
    with runlog.stage("bill"):
        wv = openpyxl.load_workbook(path, data_only=True).active
        wf = openpyxl.load_workbook(path, data_only=False).active
        comments = {}
        for row in wf.iter_rows(min_row=1, max_row=wf.max_row, min_col=1, max_col=12):
            for c in row:
                if c.comment:
                    comments[c.coordinate] = re.sub(r"\s+", " ", c.comment.text).strip()
        sections, lines = [], []
        seq_by_building = defaultdict(int)
        first_of: dict[int, tuple[str, str]] = {}
        current = None
        unknown_units = []
        seen_ids = set()
        for r in range(FIRST_DATA_ROW, TOTALS["temporary"]):
            a, b, c, d, e, f = (wv.cell(r, i).value for i in range(1, 7))
            if all(v is None for v in (a, b, c, d, e, f)):
                continue
            blank_qty = c in (None, 0, 0.0, "") and d in (None, 0, 0.0, "")
            parts = _header_parts(a)
            is_float_header = isinstance(a, float) and not isinstance(a, bool) and a != 0 and blank_qty
            if (parts or is_float_header) and blank_qty and b not in (None, ""):
                title = str(b).strip()
                if parts:
                    code = ".".join(parts)
                    building_no = int(parts[0])
                    parent = ".".join(parts[:-1]) if len(parts) > 2 else None
                    repaired = "," in str(a)
                else:
                    building_no = int(a)
                    seq_by_building[building_no] += 1
                    code = f"{building_no}.{seq_by_building[building_no]}"
                    parent = None
                    repaired = str(a) != code
                    if abs(float(code) - a) > 1e-9:
                        runlog.warn("bill", f"section code {code} does not match stored {a} at row {r}", row=r)
                named = _named_building(title)
                if named:
                    building = named
                    first_of.setdefault(building_no, (code, named))
                elif building_no in first_of:
                    building = first_of[building_no][1]
                    runlog.event("bill", "info",
                                 f"{code} has no building in the title; inherits {building} from section {first_of[building_no][0]}")
                else:
                    building = "site"
                    first_of[building_no] = (code, "site")
                current = {"code": code, "stored_code": a, "row": r, "building_no": building_no,
                           "title": title, "trade": _trade(title), "building": building,
                           "code_repaired": repaired, "parent": parent, "mark": _mark(title), "lines": []}
                sections.append(current)
                continue
            if current is None or c in (None, 0, 0.0, ""):
                runlog.warn("bill", f"row {r} is not a header or a line", row=r, a=a, b=b)
                continue
            unit, known = canonical_unit(c)
            item = int(a) if isinstance(a, (int, float)) else None
            line_id = f"{current['code']}.{item}" if item else f"{current['code']}.r{r}"
            if line_id in seen_ids:
                runlog.warn("bill", f"item number repeats in section {current['code']} at row {r}; id uses the row",
                            row=r)
                line_id = f"{current['code']}.r{r}"
            seen_ids.add(line_id)
            line = {
                "id": line_id,
                "row": r, "section": current["code"], "item": item, "description": str(b).strip() if b else "",
                "description_raw": b, "unit_raw": c, "unit": unit, "unit_known": known,
                "qty": _num(d), "rate": _num(e), "amount": _num(f), "building": current["building"],
                "trade": current["trade"], "mark": current.get("mark"), "comment": comments.get(f"B{r}"),
                "progress_qty": _num(wv.cell(r, 7).value), "progress_amount": _num(wv.cell(r, 8).value),
                "formula_desc": str(wf.cell(r, 2).value or ""),
            }
            if not known:
                unknown_units.append(line["id"])
                runlog.warn("bill", f"unknown unit '{c}' on line {line['id']} (row {r})", line=line["id"], row=r)
            lines.append(line)
            current["lines"].append(line["id"])
        totals = {k: _num(wv.cell(r, 6).value) for k, r in TOTALS.items()}
        totals["contract_price_c5"] = _num(wv["C5"].value)
        totals["progress_total_h2335"] = _num(wv.cell(TOTALS["total"], 8).value)
        line_sum = sum(l["amount"] or 0.0 for l in lines)
        chain = _totals_chain(line_sum)
        external = sorted({m.group(0) for l in lines for m in re.finditer(r"\[\d+\]", l["formula_desc"])})
        runlog.event("bill", "info", f"{len(sections)} sections, {len(lines)} lines, line sum {line_sum:,.2f}")
        return {"sections": sections, "lines": lines, "totals": totals, "line_sum": line_sum, "chain": chain,
                "comments": comments, "unknown_units": unknown_units, "external_links": external,
                "source": str(path)}


def _totals_chain(line_sum: float) -> dict:
    temporary = line_sum * 0.018
    contingency = (line_sum + temporary) * 0.02
    subtotal = line_sum + temporary + contingency - 0.02
    vat = subtotal * 0.18
    return {"line_sum": line_sum, "temporary_1_8": temporary, "contingency_2": contingency,
            "subtotal_minus_0_02": subtotal, "vat_18": vat, "total": subtotal + vat,
            "formula": "SUM(F11:F2330); ×1.8%; (sum+temp)×2%; −0.02; ×18% VAT"}
