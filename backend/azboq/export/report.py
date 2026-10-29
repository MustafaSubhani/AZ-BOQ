"""Discrepancy report in our own style: counts, then matched, different and not on a drawing."""
from pathlib import Path

import openpyxl
import pymupdf
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .. import config

LISTS = [("different", "Different", "Bill and drawing disagree"),
         ("matched", "Matched", "Equals a measured item, is printed on a drawing, or repeats a checked line"),
         ("not_found", "Not on a drawing", "No measured item and the quantity is not printed on a drawing of this building"),
         ("blocked", "Blocked", "A measured item is missing an input"),
         ("review", "Needs a look", "Only weak candidates")]
HEAD = ["Line", "Description (Azerbaijani)", "Unit", "Bill quantity", "Our quantity", "Gap", "Gap %", "Status", "Reason",
        "Line total AZN"]


def write_report_xlsx(report: dict, path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Summary"
    thin = Side(style="thin", color="E4E7EB")
    bold = Font(name="Noto Sans", bold=True, size=11)
    base = Font(name="Noto Sans", size=10)
    ws.append(["Hadrut fire station · drawing-to-bill check"])
    ws["A1"].font = Font(name="Noto Sans", bold=True, size=14)
    ws.append([])
    ws.append(["Status", "Lines", "Bill value AZN"])
    for c in ws[3]:
        c.font = bold
    for key, title, _ in LISTS:
        rows = report["lists"].get(key, [])
        ws.append([title, len(rows), round(sum(r["amount"] or 0 for r in rows), 2)])
    ws.append(["Total", sum(len(report["lists"].get(k, [])) for k, *_ in LISTS), report["total_value"]])
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 18
    for key, title, note in LISTS:
        sh = wb.create_sheet(title[:31])
        sh.append([title])
        sh["A1"].font = Font(name="Noto Sans", bold=True, size=13)
        sh.append([note])
        sh["A2"].font = Font(name="Noto Sans", size=10, color="8B919A")
        sh.append(HEAD)
        for c in sh[3]:
            c.font = bold
            c.fill = PatternFill("solid", fgColor="F7F7F8")
            c.border = Border(bottom=thin)
        for r in report["lists"].get(key, []):
            sh.append([r["id"], r["description"], r["unit"], r["bill_qty"], r["our_qty"], r["gap"],
                       None if r["gap_pct"] is None else round(r["gap_pct"], 2), r["status"], r["reason"], r["amount"]])
        for row in sh.iter_rows(min_row=4):
            for c in row:
                c.font = base
                c.alignment = Alignment(vertical="top", wrap_text=c.column in (2, 9))
                c.border = Border(bottom=thin)
        for i, w in enumerate([10, 70, 8, 14, 14, 12, 9, 11, 60, 14], start=1):
            sh.column_dimensions[get_column_letter(i)].width = w
        sh.freeze_panes = "A4"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return str(path)


def write_report_pdf(report: dict, path: Path):
    regular = config.FONT_DIR / "NotoSans-Regular.ttf"
    boldf = config.FONT_DIR / "NotoSans-Bold.ttf"
    doc = pymupdf.open()
    W, H = 842, 595
    state = {"page": None, "y": 0}

    def new_page():
        p = doc.new_page(width=W, height=H)
        p.insert_font(fontname="N", fontfile=str(regular))
        p.insert_font(fontname="B", fontfile=str(boldf))
        state["page"], state["y"] = p, 40
        return p

    def text(x, s, size=9, bold=False, color=(0.12, 0.14, 0.16), width=None):
        p = state["page"]
        if width:
            rect = pymupdf.Rect(x, state["y"] - size, x + width, state["y"] + size * 3)
            p.insert_textbox(rect, s, fontsize=size, fontname="B" if bold else "N", color=color)
        else:
            p.insert_text((x, state["y"]), s, fontsize=size, fontname="B" if bold else "N", color=color)

    new_page()
    text(40, "Hadrut fire station · drawing-to-bill check", 16, True)
    state["y"] += 22
    text(40, "Ərazi: Xocavənd, Hadrut · Sifariş 9335 · Azerbaijani descriptions are kept as written in the bill.", 9,
         color=(0.55, 0.57, 0.6))
    state["y"] += 26
    for key, title, note in LISTS:
        rows = report["lists"].get(key, [])
        text(40, f"{title}: {len(rows)} lines, {sum(r['amount'] or 0 for r in rows):,.2f} AZN of line value", 10, True)
        state["y"] += 14
    for key, title, note in LISTS[:3]:
        rows = report["lists"].get(key, [])
        new_page()
        text(40, f"{title} ({len(rows)})", 14, True)
        state["y"] += 16
        text(40, note, 9, color=(0.55, 0.57, 0.6))
        state["y"] += 20
        cols = [(40, "Line"), (95, "Description"), (430, "Unit"), (465, "Bill"), (530, "Ours"), (595, "Reason")]
        for x, h in cols:
            text(x, h, 8, True, color=(0.55, 0.57, 0.6))
        state["y"] += 12
        for r in rows[:400]:
            if state["y"] > H - 40:
                new_page()
            text(40, r["id"], 8)
            text(95, r["description"][:95], 8, width=330)
            text(430, r["unit"], 8)
            text(465, f"{r['bill_qty']:g}", 8)
            text(530, "—" if r["our_qty"] is None else f"{r['our_qty']:g}", 8)
            text(595, (r["reason"] or "")[:120], 7.5, width=210, color=(0.25, 0.27, 0.31))
            state["y"] += 24
        if len(rows) > 400:
            text(40, f"… {len(rows) - 400} more lines in the Excel report.", 8, color=(0.55, 0.57, 0.6))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return str(path)
