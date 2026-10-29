"""Week-1 spike: write the bill with no quantity changes, finish it in Excel, compare with the original."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from azboq import config  # noqa: E402
from azboq.export.client_bill import excel_finish, write_client_bill  # noqa: E402
from azboq.export.fidelity import compare_print, compare_styles, compare_values  # noqa: E402

out = config.EXPORT_DIR / "spike" / "BOQ-Hadrut-identity.xlsx"
pdf = out.with_suffix(".pdf")
info = write_client_bill(out)
print("written", json.dumps({k: v for k, v in info.items() if k != "changed_rows"}, ensure_ascii=False))
print("styles after openpyxl:", json.dumps(compare_styles(config.BILL_PATH, out), ensure_ascii=False, default=str)[:1500])
fin = excel_finish(out, pdf)
print("excel:", fin)
print("styles after Excel save:", json.dumps(compare_styles(config.BILL_PATH, out), ensure_ascii=False, default=str)[:1500])
print("values after Excel:", compare_values(config.BILL_PATH, out, set()))
print("print:", compare_print(config.BILL_PDF_PATH, pdf))
