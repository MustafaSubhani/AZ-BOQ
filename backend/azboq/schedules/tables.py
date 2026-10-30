"""Schedules drawn as text plus ruling lines, in a PDF or a DXF.

One page can hold two tables side by side. Column bands come from the vertical
rules, rows from the horizontal rules, and a column's unit comes from its header.
A floor name in a row (Texniki döşəməaltı, 1-ci mərtəbə) heads the rows below it.
"""
import re
from collections import defaultdict

import pymupdf

from ..text.legacy import fold_mixed_words
from ..text.normalise import fold_key, numbers_in

HEADER_WORDS = ("sahə", "sahe", "tipi", "otaq", "mövqe", "movqe", "ölçü", "olcu", "cəmi", "cemi", "qeyd")
FLOOR_WORDS = (
    ("floor_2", ("2-ci mertebe", "2 ci mertebe")),
    ("floor_1", ("1-ci mertebe", "1 ci mertebe")),
    ("basement", ("texniki dosemealti", "zirzemi")),
    ("external", ("artirma", "xarici doseme")),
)
UNIT_WORD = re.compile(r"(m²|m2|m³|m3|kq|kg|ədəd|eded|mm)", re.I)
UNIT_CANON = {"m2": "m²", "m²": "m²", "m3": "m³", "m³": "m³", "kq": "kg", "kg": "kg", "eded": "each", "ədəd": "each", "mm": "mm"}


def split_room_run(token: str, known: set[str], prev: int | None) -> list[str] | None:
    """'161819' after 15 -> ['16', '18', '19']. None when more than one split fits."""
    sols = []

    def walk(i, acc):
        if i == len(token):
            sols.append(acc)
            return
        for n in (2, 1, 3):
            part = token[i:i + n]
            if len(part) == n and part[0] != "0" and part in known:
                last = int(acc[-1]) if acc else prev
                if last is None or int(part) >= last:
                    walk(i + n, acc + [part])

    walk(0, [])
    return sols[0] if len(sols) == 1 else None


def _cluster(vals, tol=1.6):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol:
            out.append(v)
        else:
            out[-1] = (out[-1] + v) / 2
    return out


def ruling_lines(page) -> tuple[list, list]:
    """Horizontal and vertical rule segments: (position, start, end)."""
    horiz, vert = [], []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            a, b = item[1], item[2]
            if abs(a.y - b.y) < 0.8 and abs(a.x - b.x) > 10:
                horiz.append((round((a.y + b.y) / 2, 1), min(a.x, b.x), max(a.x, b.x)))
            elif abs(a.x - b.x) < 0.8 and abs(a.y - b.y) > 10:
                vert.append((round((a.x + b.x) / 2, 1), min(a.y, b.y), max(a.y, b.y)))
    return horiz, vert


def _page_lines(page) -> list[dict]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = fold_mixed_words(re.sub(r"\s+", " ", "".join(s["text"] for s in line["spans"])).strip())
            if text:
                lines.append({"text": text, "bbox": [round(v, 1) for v in line["bbox"]]})
    return lines


def _band(val, edges):
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if lo - 1 <= val <= hi + 1:
            return i
    return None


def _floor(text: str) -> str | None:
    key = fold_key(text)
    # The basement heading is often in a legacy font, so "döşəmə" does not fold to "doseme".
    if "texniki" in key and "mertebe" in key and "1-ci" not in key and "2-ci" not in key:
        return "basement"
    for name, words in FLOOR_WORDS:
        if any(re.search(rf"(^|[^a-z0-9]){re.escape(w)}([^a-z0-9]|$)", key) for w in words):
            return name
    return None


def _unit(header: str) -> str | None:
    text = header or ""
    m = UNIT_WORD.search(text)
    if m:
        token = m.group(1).lower()
        return UNIT_CANON.get(token, m.group(1))
    key = fold_key(text)
    if key in ("h", "b") or key.startswith("b ") or "olcu" in key:
        return "mm"
    if key in ("cemi", "1", "2") or "tex" in key or "mertebe say" in key:
        return "each"
    return None


def _table_spans(vert) -> list[tuple[float, float]]:
    """Side-by-side schedules. Outer rules are the long verticals; a shorter table still counts."""
    if not vert:
        return []
    height = max(b for _, _, b in vert) - min(a for _, a, _ in vert)
    spans = []

    def take(frames):
        xs = [x for x, _, _ in vert]
        for i, x0 in enumerate(frames):
            if any(a - 8 <= x0 <= b + 8 for a, b in spans):
                continue
            candidates = [x1 for x1 in frames[i + 1:] if 350 <= x1 - x0 <= 700]
            if not candidates:
                continue
            x1 = min(candidates)
            extra = [x for x in xs if x1 < x <= x1 + 90]
            spans.append((x0, max(extra) if extra else x1))

    long = _cluster([x for x, y0, y1 in vert if y1 - y0 > height * 0.55], 4)
    medium = _cluster([x for x, y0, y1 in vert if y1 - y0 > max(160, height * 0.2)], 4)
    take(long)
    take(medium)
    return spans


def _one_table(lines, horiz, vert, x0, x1, page) -> dict | None:
    frame = max((y1 - y0 for x, y0, y1 in vert if abs(x - x0) < 6 or abs(x - x1) < 6), default=200)
    # Short lines inside a drawn window or a floor sketch are not column borders.
    cols = _cluster([x0, x1] + [x for x, y0, y1 in vert if x0 - 2 <= x <= x1 + 2 and y1 - y0 > max(80, frame * 0.22)], 2)
    if len(cols) < 3:
        return None
    rows_y = _cluster([y for y, a, b in horiz if b - a > (x1 - x0) * 0.45 and a < x1 and b > x0], 2)
    if len(rows_y) < 3:
        return None
    cells = defaultdict(list)
    for ln in lines:
        box = ln["bbox"]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        c, r = _band(cx, cols), _band(cy, rows_y)
        if c is None or r is None:
            continue
        cells[(r, c)].append(ln)
    grid = []
    for r in range(len(rows_y) - 1):
        row = []
        for c in range(len(cols) - 1):
            parts = cells.get((r, c), [])
            text = " ".join(p["text"] for p in parts).strip()
            box = None
            if parts:
                box = [min(p["bbox"][0] for p in parts), min(p["bbox"][1] for p in parts),
                       max(p["bbox"][2] for p in parts), max(p["bbox"][3] for p in parts)]
            row.append({"text": text, "bbox": box})
        grid.append(row)
    header_end = 0
    for i, row in enumerate(grid[:6]):
        blob = fold_key(" ".join(cell["text"] for cell in row))
        if any(w in blob for w in HEADER_WORDS):
            header_end = i + 1
    if header_end == 0:
        return None
    headers = []
    for c in range(len(cols) - 1):
        headers.append(" ".join(grid[r][c]["text"] for r in range(header_end) if grid[r][c]["text"]).strip())
    units = [_unit(h) for h in headers]
    title = " ".join(grid[0][c]["text"] for c in range(len(headers)) if grid[0][c]["text"])[:80]
    body = []
    floor = None
    for row in grid[header_end:]:
        blob = " ".join(cell["text"] for cell in row)
        texts = [cell["text"] for cell in row if cell["text"]]
        big = any(numbers_in(t) and abs(numbers_in(t)[0][1]) >= 20 and len(t) < 16 for t in texts)
        if texts and not big and (any(w in fold_key(blob) for w in HEADER_WORDS) or any(_unit(t) for t in texts)):
            for c, cell in enumerate(row):
                if not cell["text"]:
                    continue
                headers[c] = (headers[c] + " " + cell["text"]).strip()
                found = _unit(cell["text"]) or _unit(headers[c])
                if found:
                    units[c] = found
            continue
        named = _floor(blob)
        numbers = [cell for cell in row if numbers_in(cell["text"]) and len(cell["text"]) < 16]
        if named and not numbers:
            floor = named
            body.append({"floor": floor, "section": True, "text": blob.strip()[:120], "cells": []})
            continue
        if not any(cell["text"] for cell in row):
            continue
        body.append({"floor": floor, "section": False, "cells": [
            {**cell, "header": headers[c], "unit": units[c]} for c, cell in enumerate(row) if cell["text"]
        ]})
    _apply_floor_headings(body, lines, x0, x1)
    blob = fold_key(title + " " + " ".join(headers))
    if any(w in blob for w in ("eksplik", "bezek", "tavan", "doseme")):
        for row in body:
            for cell in row.get("cells") or []:
                if _plain_area(cell["text"]) and cell.get("unit") in (None, "each"):
                    cell["unit"] = "m²"
    return {"page": page, "bbox": [round(x0, 1), round(rows_y[0], 1), round(x1, 1), round(rows_y[-1], 1)],
            "title": title, "columns": [{"header": h, "unit": u} for h, u in zip(headers, units)], "rows": body}


def _apply_floor_headings(body, lines, x0, x1) -> None:
    """A floor name printed above a row labels that row, even when it sits between the ruled bands."""
    headings = []
    for ln in lines:
        box = ln["bbox"]
        if not (x0 - 4 <= (box[0] + box[2]) / 2 <= x1 + 4):
            continue
        if len(ln["text"]) > 80 or "mm" in fold_key(ln["text"]):
            continue
        named = _floor(ln["text"])
        if named:
            headings.append((box[1], named))
    if not headings:
        return
    headings.sort()
    for row in body:
        if row.get("section"):
            continue
        ys = [c["bbox"][1] for c in row.get("cells") or [] if c.get("bbox")]
        if not ys:
            continue
        above = [name for hy, name in headings if hy <= max(ys) + 4]
        if above:
            row["floor"] = above[-1]


def _plain_area(text: str) -> bool:
    token = (text or "").strip().replace(" ", "")
    if not re.fullmatch(r"\d+[.,]\d+", token):
        return False
    vals = numbers_in(text)
    return bool(vals) and abs(vals[0][1]) >= 10


def tables_on_page(page, page_no: int) -> list[dict]:
    lines = _page_lines(page)
    horiz, vert = ruling_lines(page)
    found = []
    for x0, x1 in _table_spans(vert):
        if any(_span_overlap((x0, x1), (t["bbox"][0], t["bbox"][2])) > 0.6 for t in found):
            continue
        table = _one_table(lines, horiz, vert, x0, x1, page_no)
        if table and table["rows"]:
            found.append(table)
    from .openings import attach_sills
    attach_sills(page, found)
    return found


def _span_overlap(a, b) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    small = min(a[1] - a[0], b[1] - b[0])
    return inter / small if small else 0.0


def read_pdf(path, pages: list[int] | None = None) -> list[dict]:
    doc = pymupdf.open(path)
    chosen = pages if pages is not None else range(len(doc))
    out = []
    for i in chosen:
        out.extend(tables_on_page(doc[i], i))
    return out
