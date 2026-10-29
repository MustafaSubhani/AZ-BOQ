import sys
import zipfile
import re

sys.stdout.reconfigure(encoding="utf-8")
import openpyxl  # noqa: E402
from azboq import config  # noqa: E402

ws = openpyxl.load_workbook(config.BILL_PATH).active
ps = ws.page_setup
print("scale", ps.scale, "fitToWidth", ps.fitToWidth, "fitToHeight", ps.fitToHeight, "paper", ps.paperSize, ps.orientation)
print("fitToPage", ws.sheet_properties.pageSetUpPr.fitToPage)
print("default row height", ws.sheet_format.defaultRowHeight, "customHeight", ws.sheet_format.customHeight)
none_rows = [r for r in range(10, 2340) if ws.row_dimensions[r].height is None]
print("rows without height", len(none_rows), none_rows[:10])
z = zipfile.ZipFile(config.BILL_PATH)
x = z.read("xl/worksheets/sheet1.xml").decode("utf8")
print(re.findall(r"<sheetFormatPr[^>]*>", x))
print(re.findall(r"<pageSetup[^>]*>", x))
print(re.findall(r'<row r="62"[^>]*>', x), re.findall(r'<row r="11"[^>]*>', x))
print(re.findall(r"<rowBreaks[^>]*>", x)[:2], x.count("<brk "))
