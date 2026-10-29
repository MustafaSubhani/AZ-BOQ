"""Write every export: filled client bill, its PDF print, the discrepancy report, the generated bill."""
import json
import time

from .. import config, runlog, store
from .client_bill import excel_finish, write_client_bill
from .fidelity import compare_print, compare_styles, compare_values
from .generated_bill import write_generated_bill
from .report import write_report_pdf, write_report_xlsx


def export_all(use_excel: bool = True) -> dict:
    bill, report = store.get("bill"), store.get("report")
    out_dir = config.EXPORT_DIR
    info = {"written_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with runlog.stage("export"):
        by_row = {l["row"]: l for l in bill["lines"]}
        quantities, notes, evidence = {}, {}, []
        for l in bill["lines"]:
            r = report["lines"][l["id"]]
            if r["status"] in ("matched", "different") and r.get("our_qty") is not None and r.get("item"):
                if r["status"] == "different":
                    quantities[l["row"]] = r["our_qty"]
                    notes[l["row"]] = f"AZ-BOQ: bill {l['qty']:g}, drawing {r['our_qty']:g} {l['unit']}. {r['reason']}"
            src = (r.get("sources") or [{}])[0]
            evidence.append({"line": l["id"], "row": l["row"], "status": r["status"], "our_quantity": r.get("our_qty"),
                             "bill_quantity": l["qty"], "unit": l["unit"], "method": r.get("method"),
                             "source": src.get("file_name") or r.get("item") or "", "reason": r["reason"]})
        filled = out_dir / "BOQ-Hadrut-checked.xlsx"
        res = write_client_bill(filled, quantities, notes, evidence)
        info["client_bill"] = {k: v for k, v in res.items() if k != "changed_rows"}
        info["client_bill"]["changed_rows"] = res["changed_rows"]
        info["client_bill_styles"] = compare_styles(config.BILL_PATH, filled)
        if use_excel:
            pdf = out_dir / "BOQ-Hadrut-checked.pdf"
            fin = excel_finish(filled, pdf)
            info["excel"] = fin
            info["client_bill_styles_after_excel"] = compare_styles(config.BILL_PATH, filled)
            info["client_bill_values_after_excel"] = compare_values(config.BILL_PATH, filled, set(quantities))
            info["print"] = compare_print(config.BILL_PDF_PATH, pdf)
        info["report_xlsx"] = write_report_xlsx(report, out_dir / "Hadrut-discrepancy-report.xlsx")
        info["report_pdf"] = write_report_pdf(report, out_dir / "Hadrut-discrepancy-report.pdf")
        gen = write_generated_bill(bill, report, out_dir / "BOQ-Hadrut-generated.xlsx")
        info["generated_bill"] = gen
        if use_excel:
            info["generated_excel"] = excel_finish(out_dir / "BOQ-Hadrut-generated.xlsx",
                                                   out_dir / "BOQ-Hadrut-generated.pdf")
        (out_dir / "exports.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str),
                                              encoding="utf-8")
        runlog.event("export", "info", f"client bill: {len(quantities)} quantities changed; "
                     f"style diffs {info['client_bill_styles']['cell_style_diffs']}")
    return info
