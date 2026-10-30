"""Floor-schedule layers. Thickness and kg/m² are read from the layer's own text.

`B10-100mm` is 100 mm of concrete, not 10. `150x150mm` is mesh spacing; the
thickness is the last plain `<n> mm`. A kg/m² printed on another type is used
only when the rule names that type, and the note says so.
"""
import re

from ..text.normalise import fold_key
from ..values import Method, Source, Status, Value, blocked, derive

THICK = re.compile(r"(?<![x×XхХ\d.,])(\d+(?:[.,]\d+)?)\s*(?:mm|мм)(?![\w²³])", re.I)
KG_PER_M2 = re.compile(r"1\s*m\s*2?\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:kq|kg|кг)", re.I)
LAYER_START = re.compile(r"(?:^|\s)(?<!\d)(\d{1,2})\s*[.)](?=\s*[^\d\s])")


def layer_lines(text: str) -> list[str]:
    """Split a run-on cell at layer numbers: '6.Keramzit … 5.Sement …'."""
    cuts = [m.start(1) for m in LAYER_START.finditer(text or "")]
    if not cuts:
        return [text.strip()] if (text or "").strip() else []
    parts = []
    prev = 0
    for cut in cuts:
        chunk = text[prev:cut].strip()
        if chunk:
            parts.append(chunk)
        prev = cut
    tail = text[prev:].strip()
    if tail:
        parts.append(tail)
    return parts


def layers_of(cell_lines: list[str]) -> list[dict]:
    """Numbered layers; an unnumbered line continues the layer above it."""
    out = []
    for line in cell_lines:
        if LAYER_START.match(line) or not out:
            out.append({"text": line})
        else:
            out[-1]["text"] += " " + line
    for layer in out:
        hits = [m for m in THICK.finditer(layer["text"])
                if not re.search(r"\d\s*[x×XхХ]\s*$", layer["text"][:m.start()])]
        layer["thickness_mm"] = float(hits[-1].group(1).replace(",", ".")) if hits else None
        kg = KG_PER_M2.search(layer["text"])
        layer["kg_per_m2"] = float(kg.group(1).replace(",", ".")) if kg else None
    return out


def _type_no(row: dict) -> str | None:
    for cell in row.get("cells") or []:
        if "tipi" in fold_key(cell.get("header") or "") and re.fullmatch(r"\d{1,2}", cell["text"].strip()):
            return cell["text"].strip()
    return None


def _area_cell(row: dict) -> dict | None:
    for cell in row.get("cells") or []:
        if cell.get("unit") == "m²" and re.fullmatch(r"\d+(?:[.,]\d+)?", cell["text"].strip()):
            return cell
    return None


def _layer_cell(row: dict) -> dict | None:
    for cell in row.get("cells") or []:
        if cell.get("unit") == "mm" and THICK.search(cell["text"] or ""):
            return cell
    return None


def floor_rows(tables: list[dict]) -> list[dict]:
    rows = []
    for table in tables:
        blob = fold_key(table.get("title", "") + " " + " ".join(c.get("header") or "" for c in table.get("columns") or []))
        if "doseme" not in blob and "eksplik" not in blob:
            continue
        for row in table.get("rows") or []:
            if row.get("section"):
                continue
            area = _area_cell(row)
            layer = _layer_cell(row)
            type_no = _type_no(row)
            if area is None or layer is None or type_no is None or not row.get("floor"):
                continue
            rows.append({
                "floor": row["floor"],
                "type_no": type_no,
                "page": table.get("page"),
                "area": float(area["text"].replace(",", ".")),
                "area_cell": area,
                "layer_cell": layer,
                "layers": layers_of(layer_lines(layer["text"])),
            })
    return rows


def _find(rows, floor, type_no):
    found = [r for r in rows if r["floor"] == floor and r["type_no"] == str(type_no)]
    return found


def _cell_value(sha, file_name, page, cell, number, unit, printed: str | None = None) -> Value:
    src = Source(sha, file_name, {"kind": "pdf_span", "page": page, "bbox": cell.get("bbox")},
                 cell.get("text"), printed if printed is not None else cell.get("text"))
    return Value(float(number), unit, Method.SCHEDULE, Status.EXTRACTED, sources=(src,))


def _layer_for(row: dict, material: str | None, want_kg: bool) -> dict | None:
    hits = []
    for layer in row["layers"]:
        text = fold_key(layer["text"])
        if material and material not in text:
            continue
        if want_kg and layer["kg_per_m2"] is None:
            continue
        if not want_kg and layer["thickness_mm"] is None:
            continue
        hits.append(layer)
    if len(hits) != 1:
        return None
    return hits[0]


def layer_measure(rows: list[dict], rule: dict, sha: str, file_name: str) -> Value:
    """Area × thickness, or area × kg/m². The factor is a cell on the same schedule."""
    found = _find(rows, rule["floor"], rule["type_no"])
    if len(found) != 1:
        return blocked(rule["unit"], [rule["id"]], [file_name],
                       f"floor {rule['floor']} type {rule['type_no']} was not found once", Method.SCHEDULE)
    row = found[0]
    want_kg = rule["unit"] == "t"
    layer = _layer_for(row, rule.get("material"), want_kg)
    borrowed = None
    if layer is None and want_kg and rule.get("weight_from_type"):
        donor = _find(rows, rule["floor"], rule["weight_from_type"])
        if len(donor) == 1:
            borrowed = _layer_for(donor[0], rule.get("material"), True)
            layer = next((L for L in row["layers"] if rule.get("material", "") in fold_key(L["text"])), None)
            if layer is None:
                layer = {"text": "", "thickness_mm": None, "kg_per_m2": None}
    if layer is None or (want_kg and (borrowed or layer)["kg_per_m2"] is None) or (not want_kg and layer["thickness_mm"] is None):
        return blocked(rule["unit"], [rule["id"]], [file_name],
                       f"no {'weight' if want_kg else 'thickness'} for {rule.get('material') or 'the layer'}",
                       Method.SCHEDULE)
    factor_row = row
    factor = layer["kg_per_m2"] if want_kg else layer["thickness_mm"]
    factor_cell = row["layer_cell"]
    note = ""
    if borrowed is not None:
        factor = borrowed["kg_per_m2"]
        factor_row = _find(rows, rule["floor"], rule["weight_from_type"])[0]
        factor_cell = factor_row["layer_cell"]
        note = f"weight per m² printed for type {rule['weight_from_type']}, applied to type {rule['type_no']}'s mesh layer"
    area_v = _cell_value(sha, file_name, row["page"], row["area_cell"], row["area"], "m²")
    factor_unit = "kg/m²" if want_kg else "mm"
    printed = None
    if want_kg:
        hit = KG_PER_M2.search((borrowed or layer)["text"])
        if hit:
            printed = hit.group(0)
    factor_v = _cell_value(sha, file_name, factor_row["page"], factor_cell, factor, factor_unit, printed)
    if want_kg:
        formula = "area_m2 × kg_per_m2 ÷ 1000"
        value = derive("t", formula, lambda area_m2, kg_per_m2: area_m2 * kg_per_m2 / 1000,
                       area_m2=area_v, kg_per_m2=factor_v)
    else:
        formula = "area_m2 × thickness_mm ÷ 1000"
        value = derive("m³", formula, lambda area_m2, thickness_mm: area_m2 * thickness_mm / 1000,
                       area_m2=area_v, thickness_mm=factor_v)
    if not note:
        return value
    return Value(value.value, value.unit, value.method, value.status, formula=value.formula,
                 inputs=value.inputs, note=note)
