"""Schedules drawn as text on a line grid in a DWG, on the table layers.

The PDF reader never sees these. A steel table such as "Polad sərfi cədvəli" is
horizontal and vertical rules with the mark, the bar class and the kilograms in the cells.
"""
import re
from collections import defaultdict

from ..text.normalise import fold_key
from .tables import HEADER_WORDS, _band, _cluster, _unit

_DECIMAL = re.compile(r"\d+[.,]\d+")
_KG_HEADER = re.compile(r"Ø|A[-\s]*240|A500|A-[lI]\b|Yekun|Cəmi", re.I)
_BAR_CLASS = re.compile(r"A[-\s]*240|A500|A-[lI]\b", re.I)
_TITLE_WORD = ("cedvel", "serfi", "eksplik")


def grids_in_dump(dump: dict) -> list[dict]:
    lines = [ln for ln in dump.get("lines") or [] if ln.get("role") == "table"]
    polys = [p for p in dump.get("polys") or [] if p.get("role") == "table"]
    texts = [t for t in dump.get("texts") or [] if (t.get("text") or "").strip()]
    groups = _components(_segments(lines, polys))
    tables = []
    for group in groups:
        table = _one(group, texts)
        if table:
            tables.append(table)
    return tables


def _segments(lines, polys=None) -> list[tuple]:
    out = []

    def add(a, b):
        if len(a) < 2 or len(b) < 2:
            return
        if abs(a[1] - b[1]) <= 1:
            out.append(("h", min(a[0], b[0]), max(a[0], b[0]), (a[1] + b[1]) / 2))
        elif abs(a[0] - b[0]) <= 1:
            out.append(("v", min(a[1], b[1]), max(a[1], b[1]), (a[0] + b[0]) / 2))

    for ln in lines:
        add(ln.get("a") or [], ln.get("b") or [])
    for poly in polys or []:
        pts = [p for p in (poly.get("pts") or []) if len(p) >= 2]
        if poly.get("closed") and len(pts) > 2 and pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        for a, b in zip(pts, pts[1:]):
            add(a, b)
    return out


def _components(segs: list[tuple]) -> list[list[tuple]]:
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if _touch(segs[i], segs[j]):
                parent[find(j)] = find(i)
    groups = defaultdict(list)
    for i, seg in enumerate(segs):
        groups[find(i)].append(seg)
    return list(groups.values())


def _touch(p, q, tol=8) -> bool:
    def near(seg, x, y):
        if seg[0] == "h":
            return abs(y - seg[3]) <= tol and seg[1] - tol <= x <= seg[2] + tol
        return abs(x - seg[3]) <= tol and seg[1] - tol <= y <= seg[2] + tol

    ends = [(p[1], p[3]), (p[2], p[3])] if p[0] == "h" else [(p[3], p[1]), (p[3], p[2])]
    ends2 = [(q[1], q[3]), (q[2], q[3])] if q[0] == "h" else [(q[3], q[1]), (q[3], q[2])]
    return any(near(q, x, y) for x, y in ends) or any(near(p, x, y) for x, y in ends2)


def _one(segs, texts) -> dict | None:
    horiz, vert = [], []
    xs, ys = [], []
    for kind, a, b, pos in segs:
        if kind == "h":
            horiz.append((pos, a, b))
            xs += [a, b]
            ys.append(pos)
        else:
            vert.append((pos, a, b))
            ys += [a, b]
            xs.append(pos)
    if len(horiz) < 2 or len(vert) < 2:
        return None
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    width, height = x1 - x0, y1 - y0
    if width < 50 or height < 50:
        return None
    tol = max(2.0, min(width, height) * 0.004)
    cols = _cluster([x0, x1] + [x for x, a, b in vert if b - a > height * 0.22], tol)
    rows_y = sorted(_cluster([y for y, a, b in horiz if b - a > width * 0.45], tol))
    if len(cols) < 3 or len(rows_y) < 3:
        return None
    cells = defaultdict(list)
    for t in texts:
        cx, cy = t["at"][0], t["at"][1]
        c, r = _band(cx, cols), _band(cy, rows_y)
        if c is None or r is None:
            continue
        cells[(r, c)].append(t)
    n_rows = len(rows_y) - 1
    grid = []
    boxes = []
    for r in range(n_rows - 1, -1, -1):
        row, row_boxes = [], []
        for c in range(len(cols) - 1):
            parts = sorted(cells.get((r, c), []), key=lambda t: (-t["at"][1], t["at"][0]))
            seen, bits = set(), []
            box = None
            for part in parts:
                bit = " ".join(part["text"].split())
                if bit and bit not in seen:
                    seen.add(bit)
                    bits.append(bit)
                if part.get("bbox"):
                    box = part["bbox"]
            row.append(" ".join(bits))
            row_boxes.append(box)
        grid.append(row)
        boxes.append(row_boxes)
    header_end, headers = _headers(grid)
    if header_end == 0:
        return None
    units = [_unit(h) for h in headers]
    if any(u == "kg" for u in units):
        for i, header in enumerate(headers):
            if units[i] is None and _KG_HEADER.search(header or ""):
                units[i] = "kg"
    body = []
    for r, row in enumerate(grid):
        if r < header_end or not any(row):
            continue
        body.append({"floor": None, "section": False, "cells": [
            {"text": row[c], "bbox": boxes[r][c], "header": headers[c], "unit": units[c]}
            for c in range(len(row)) if row[c]
        ]})
    if not body:
        return None
    title = _title(texts, x0, x1, y1, height) or " ".join(bit for bit in grid[0] if bit)
    return {
        "bbox": [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
        "title": title[:80],
        "columns": [{"header": h, "unit": u} for h, u in zip(headers, units)],
        "rows": body,
    }


def _headers(grid) -> tuple[int, list[str]]:
    end = 0
    for i, row in enumerate(grid):
        if any(_DECIMAL.search(cell) for cell in row):
            break
        end = i + 1
    return _compose(grid, end)


def _compose(grid, end: int) -> tuple[int, list[str]]:
    if end == 0 or not grid:
        return 0, []
    blob = fold_key(" ".join(cell for row in grid[:end] for cell in row))
    if not any(word in blob for word in HEADER_WORDS):
        return 0, []
    n = len(grid[0])
    acc = [[] for _ in range(n)]
    for row in grid[:end]:
        labels = [(c, row[c]) for c in range(n) if row[c]]
        for c, text in labels:
            acc[c].append(text)
        classes = [(c, text) for c, text in labels if _BAR_CLASS.search(text)]
        if not classes:
            continue
        blocked = {c for c in range(n) if acc[c] and not row[c]}
        for c in range(n):
            if row[c] or c in blocked:
                continue
            best = None
            for lc, text in classes:
                if any(min(c, lc) < b < max(c, lc) for b in blocked):
                    continue
                dist = abs(c - lc)
                if best is None or dist < best[0]:
                    best = (dist, text)
            if best:
                acc[c].append(best[1])
    return end, [" ".join(parts) for parts in acc]


def _title(texts, x0, x1, y1, height) -> str:
    hits = []
    for t in texts:
        x, y = t["at"]
        if x0 <= x <= x1 and y1 < y <= y1 + 0.35 * height:
            hits.append(t)
    if not hits:
        return ""
    closest = min(hits, key=lambda t: t["at"][1] - y1)
    text = " ".join(closest["text"].split())
    key = fold_key(text)
    return text if any(word in key for word in _TITLE_WORD) else ""
