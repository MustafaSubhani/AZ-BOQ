"""Steel schedules stored as ACAD_TABLE entities.

The depot drawing keeps these as table cells, not as text on a line grid.
A summary table names the element and the kilograms by bar class. A bar table
names each cut, its length, its count and its mass.
"""
import re

from ..text.normalise import fold_key
from .grids import _BAR_CLASS, _DECIMAL, _KG_HEADER, _compose, _title
from .tables import HEADER_WORDS, _unit


def acad_tables(dump: dict) -> list[dict]:
    texts = [t for t in dump.get("texts") or [] if (t.get("text") or "").strip() and not t.get("table")]
    out = []
    for table in dump.get("tables") or []:
        shaped = _one(table, texts)
        if shaped:
            out.append(shaped)
    return out


def _one(table: dict, texts) -> dict | None:
    cells = [c for c in table.get("cells") or [] if c.get("r") is not None and c.get("c") is not None]
    if not cells:
        return None
    n_rows = max(table.get("n_rows") or 0, max(c["r"] for c in cells) + 1)
    n_cols = max(table.get("n_cols") or 0, max(c["c"] for c in cells) + 1)
    grid = [[""] * n_cols for _ in range(n_rows)]
    at = [[None] * n_cols for _ in range(n_rows)]
    for cell in cells:
        text = " ".join((cell.get("text") or "").split())
        if not text:
            continue
        r, c = cell["r"], cell["c"]
        if grid[r][c] and text not in grid[r][c].split():
            grid[r][c] = f"{grid[r][c]} {text}"
        elif not grid[r][c]:
            grid[r][c] = text
        at[r][c] = cell.get("at")
    end = _header_end(grid)
    header_end, headers = _compose(grid, end)
    if header_end == 0:
        return None
    bbox = table.get("bbox") or [0, 0, 0, 0]
    height = abs(bbox[3] - bbox[1]) or 1
    title = _title(texts, bbox[0], bbox[2], bbox[3], height) or " ".join(bit for bit in grid[0] if bit)
    units = _units(headers, title)
    body = []
    for r, row in enumerate(grid):
        if r < header_end or not any(row):
            continue
        body.append({
            "floor": None,
            "section": not any(_DECIMAL.search(cell) for cell in row),
            "cells": [
                {"text": row[c], "bbox": at[r][c], "header": headers[c], "unit": units[c]}
                for c in range(len(row)) if row[c]
            ],
        })
    if not body:
        return None
    return {
        "handle": table.get("handle"),
        "bbox": bbox,
        "title": title[:80],
        "columns": [{"header": h, "unit": u} for h, u in zip(headers, units)],
        "rows": body,
    }


def _header_end(grid) -> int:
    """Stop before a quantity, and before a one-cell element heading such as 'S - 6'."""
    end = 0
    seen = False
    for i, row in enumerate(grid):
        if any(_DECIMAL.search(cell) for cell in row):
            break
        filled = [cell for cell in row if cell]
        blob = " ".join(filled)
        headerish = (
            any(word in fold_key(blob) for word in HEADER_WORDS)
            or bool(_BAR_CLASS.search(blob))
            or "Ø" in blob
            or len(filled) >= 3
        )
        if seen and len(filled) <= 1 and not headerish:
            break
        if not filled:
            if seen:
                break
            continue
        seen = seen or headerish
        end = i + 1
    return end


def _units(headers, title) -> list[str | None]:
    units = [_unit(h) for h in headers]
    if not any(u == "kg" for u in units) and not re.search(r"kq|kg", f"{title} {' '.join(headers)}", re.I):
        return units
    for i, header in enumerate(headers):
        if units[i] is None and _KG_HEADER.search(header or ""):
            units[i] = "kg"
    return units
