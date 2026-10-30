"""Window-schedule rows: mark, width, height, and the count the floors add up to.

B and H stay in millimetres, as printed. The area is their product times the
count, divided by 1 000 000. A count that the floor columns do not add up to
is left empty, so the area is blocked instead of guessed.
"""
import re

from ..text.normalise import fold_key
from ..values import Method, Source, Status, Value, blocked, derive

MARK = re.compile(r"^(QP|P)-\d+$|^Q-\d+\*?$", re.I)
PA = re.compile(r"Pa-\d+", re.I)
DIM = re.compile(r"\d{3,4}")
SIZE = re.compile(r"(\d{3,4})\s*[x×X]\s*(\d{3,4})\s*[x×X]\s*(\d{2,3})")


def _window_table(table: dict) -> bool:
    blob = fold_key(table.get("title", "") + " " + " ".join(c.get("header") or "" for c in table.get("columns") or []))
    return "movqe" in blob and "olcu" in blob


def resolve_count(counts: list[int]) -> int | None:
    """The total column when the other columns add up to it, or the repeated single-storey count."""
    if not counts:
        return None
    if len(counts) == 1:
        return counts[0]
    *floors, total = counts
    if sum(floors) == total:
        return total
    if len(counts) == 2 and counts[0] == counts[1]:
        return counts[0]
    return None


def attach_sills(page, tables: list[dict]) -> None:
    """The sill size is printed just past the frame: Pa-1 beside 1200x400x30(h)."""
    from .tables import _page_lines
    sizes = []
    for ln in _page_lines(page):
        m = SIZE.search(ln["text"].replace("Х", "x").replace("х", "x"))
        if not m:
            continue
        sizes.append({"length_mm": int(m.group(1)), "depth_mm": int(m.group(2)),
                      "bbox": ln["bbox"], "text": ln["text"]})
    for table in tables:
        if not _window_table(table):
            continue
        for row in table.get("rows") or []:
            pa_cell = next((c for c in row.get("cells") or [] if c.get("text") and PA.search(c["text"])), None)
            if pa_cell is None or not pa_cell.get("bbox"):
                continue
            mark = PA.search(pa_cell["text"]).group(0)
            y = (pa_cell["bbox"][1] + pa_cell["bbox"][3]) / 2
            near = [s for s in sizes if abs((s["bbox"][1] + s["bbox"][3]) / 2 - y) <= 12]
            if len(near) != 1:
                row["sill"] = {"mark": mark, "conflict": f"{mark} has {len(near)} size lines"}
                continue
            s = near[0]
            row["sill"] = {"mark": mark, "length_mm": s["length_mm"], "depth_mm": s["depth_mm"],
                           "bbox": s["bbox"], "text": s["text"]}


def opening_rows(tables: list[dict]) -> list[dict]:
    rows = []
    for table in tables:
        if not _window_table(table):
            continue
        page = table.get("page")
        for row in table.get("rows") or []:
            if row.get("section"):
                continue
            cells = row.get("cells") or []
            mark = next((c["text"].strip() for c in cells if MARK.fullmatch(c["text"].strip())), None)
            if not mark:
                continue
            material = next((c["text"] for c in cells if any(w in fold_key(c["text"]) for w in ("metal", "pvc", "mdf"))), "")
            dims = []
            for cell in cells:
                if cell.get("unit") != "mm" or len(cell["text"]) > 24:
                    continue
                found = [int(n) for n in DIM.findall(cell["text"]) if 400 <= int(n) <= 9000]
                for n in found[:2]:
                    dims.append((n, cell))
            counts = []
            for cell in cells:
                if cell.get("unit") == "each" and re.fullmatch(r"\d{1,3}", cell["text"].strip()):
                    counts.append((int(cell["text"]), cell))
            nums = [n for n, _ in counts]
            total = resolve_count(nums)
            conflict = None
            if len(dims) != 2:
                conflict = f"{mark} has {len(dims)} dimensions, not width and height"
            elif total is None:
                conflict = f"{mark} counts {nums} do not add up to the total column"
            rows.append({
                "mark": mark.upper(),
                "material": material,
                "page": page,
                "B": dims[0][0] if len(dims) >= 1 else None,
                "H": dims[1][0] if len(dims) >= 2 else None,
                "counts": nums,
                "total": total,
                "conflict": conflict,
                "cell_B": dims[0][1] if dims else None,
                "cell_H": dims[1][1] if len(dims) >= 2 else None,
                "cell_n": counts[-1][1] if total is not None and counts else None,
                "sill": row.get("sill"),
            })
    return rows


def _cell_value(sha: str, file_name: str, page, cell: dict, number: float, unit: str,
                row_label: str | None = None, col: str | None = None) -> Value:
    loc = {"kind": "pdf_span", "page": page, "bbox": cell.get("bbox"),
           "row": row_label, "col": col}
    src = Source(sha, file_name, loc, cell.get("text"), cell.get("text"))
    return Value(float(number), unit, Method.SCHEDULE, Status.EXTRACTED, sources=(src,),
                 note=f"{row_label} · {col}" if row_label and col else "")


def openings_area(rows: list[dict], marks: list[str], sha: str, file_name: str) -> Value:
    """Sum of B × H × count over the named marks. Every factor keeps the cell it was read from."""
    by = {}
    for row in rows:
        by.setdefault(row["mark"], []).append(row)
    inputs = {}
    missing = []
    keys = []
    for mark in marks:
        found = by.get(mark.upper(), [])
        key = re.sub(r"\W", "", mark.upper())
        if "*" in mark:
            key += "s"
        if len(found) != 1:
            missing.append(mark if not found else f"{mark} (printed {len(found)} times)")
            continue
        row = found[0]
        if row["conflict"] or row["total"] is None or row["B"] is None or row["H"] is None:
            missing.append(f"{mark}: {row['conflict'] or 'incomplete row'}")
            continue
        inputs[f"{key}_B_mm"] = _cell_value(sha, file_name, row["page"], row["cell_B"], row["B"], "mm", mark, "Ölçülər B")
        inputs[f"{key}_H_mm"] = _cell_value(sha, file_name, row["page"], row["cell_H"], row["H"], "mm", mark, "Ölçülər H")
        inputs[f"{key}_n"] = _cell_value(sha, file_name, row["page"], row["cell_n"], row["total"], "each", mark, "Cəmi")
        keys.append(key)
    if missing:
        return blocked("m²", missing, [file_name], "; ".join(missing), Method.DERIVED)
    formula = "(" + " + ".join(f"{k}_B_mm × {k}_H_mm × {k}_n" for k in keys) + ") ÷ 1000000"
    terms = [f"{by[m.upper()][0]['B']}×{by[m.upper()][0]['H']}×{by[m.upper()][0]['total']}" for m in marks]

    def _sum(**kw):
        return sum(kw[f"{k}_B_mm"] * kw[f"{k}_H_mm"] * kw[f"{k}_n"] for k in keys) / 1_000_000

    value = derive("m²", formula, _sum, **inputs)
    note = " + ".join(terms) + " mm²"
    return Value(value.value, value.unit, value.method, value.status, formula=value.formula,
                 inputs=value.inputs, note=note)


def sills_area(rows: list[dict], sha: str, file_name: str) -> Value:
    """Each sill is length × depth × count. Length and depth come from the size printed beside Pa-n."""
    sills = [r for r in rows if r.get("sill")]
    if not sills:
        return blocked("m²", ["sills"], [file_name], "no sill marks on the window schedule", Method.SCHEDULE)
    missing = []
    inputs = {}
    keys = []
    for row in sills:
        sill = row["sill"]
        key = re.sub(r"\W", "", sill["mark"])
        if sill.get("conflict") or row.get("total") is None or "length_mm" not in sill:
            missing.append(sill.get("conflict") or f"{sill['mark']} has no count")
            continue
        size = {"text": sill["text"], "bbox": sill["bbox"]}
        inputs[f"{key}_L_mm"] = _cell_value(sha, file_name, row["page"], size, sill["length_mm"], "mm")
        inputs[f"{key}_D_mm"] = _cell_value(sha, file_name, row["page"], size, sill["depth_mm"], "mm")
        inputs[f"{key}_n"] = _cell_value(sha, file_name, row["page"], row["cell_n"], row["total"], "each")
        keys.append(key)
    if missing:
        return blocked("m²", missing, [file_name], "; ".join(missing), Method.SCHEDULE)
    formula = "(" + " + ".join(f"{k}_L_mm × {k}_D_mm × {k}_n" for k in keys) + ") ÷ 1000000"

    def _sum(**kw):
        return sum(kw[f"{k}_L_mm"] * kw[f"{k}_D_mm"] * kw[f"{k}_n"] for k in keys) / 1_000_000

    return derive("m²", formula, _sum, **inputs)
