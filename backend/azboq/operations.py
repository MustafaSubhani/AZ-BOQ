"""Module 2, thin slice: registers seeded only from data that exists in this package.

Deliveries, measurements and invoices do not exist yet, so those registers are
empty and say what belongs in them. Fraud rules need them and are not run.
"""
from collections import Counter

from . import store


def build_operations() -> dict:
    reg, bill, sheets = store.get("register"), store.get("bill"), store.get("sheets")
    drawings = []
    for f in reg["files"]:
        if f["kind"] in ("drawing_cad", "drawing_pdf", "drawing_scan"):
            n = len(sheets["dwg"].get(f["sha256"], {}).get("regions", [])) or \
                len(sheets["pdf"].get(f["sha256"], {}).get("pages", []))
            drawings.append({"file": f["rel"], "kind": f["kind"], "discipline": f.get("discipline"),
                             "building": f.get("building"), "order": f.get("order"), "sheets": n,
                             "version": f.get("dwg_version")})
    contract = [{"id": l["id"], "description": l["description"], "unit": l["unit"], "qty": l["qty"], "rate": l["rate"],
                 "amount": l["amount"], "building": l["building"], "trade": l["trade"]} for l in bill["lines"]]
    units = Counter(l["unit_raw"] for l in bill["lines"])
    codes = {
        "buildings": sorted({l["building"] for l in bill["lines"]}),
        "trades": sorted({l["trade"] for l in bill["lines"]}),
        "units": [{"written": k, "lines": v} for k, v in units.most_common()],
        "sections": [{"code": s["code"], "title": s["title"], "building": s["building"], "trade": s["trade"]}
                     for s in bill["sections"]],
    }
    registers = [
        {"id": "drawings", "title": "Drawing register", "title_az": "Çertyoj reyestri", "workbook": "PJ_04",
         "rows": drawings, "empty_note": ""},
        {"id": "contract_bill", "title": "Contract bill", "title_az": "Müqavilə BOQ", "workbook": "PJ_12",
         "rows": contract, "empty_note": ""},
        {"id": "materials", "title": "Material receiving", "title_az": "Material qəbul reyestri", "workbook": "PJ_08",
         "rows": [], "empty_note": "Deliveries go here: date, supplier, material, quantity, unit, delivery note. "
                                    "None exist in the Hadrut package, so 'delivered above the bill line' cannot be checked yet."},
        {"id": "measurements", "title": "Measurement register", "title_az": "Ölçmə reyestri", "workbook": "PJ_12",
         "rows": [], "empty_note": "Monthly measured quantities per bill line go here (Forma 2). The bill's progress "
                                    "columns are almost all zero."},
        {"id": "invoices", "title": "Invoices", "title_az": "Qaimə reyestri", "workbook": "PJ_13",
         "rows": [], "empty_note": "Invoices and e-qaimə go here. 'Invoice above the measured quantity' and "
                                    "'same delivery entered twice' need these rows."},
    ]
    return {"registers": registers, "codes": codes,
            "fraud_rules": [
                {"id": "F1", "rule": "Delivered quantity above the bill line", "needs": ["materials", "contract_bill"],
                 "runnable": False},
                {"id": "F2", "rule": "Invoice above the measured quantity", "needs": ["invoices", "measurements"],
                 "runnable": False},
                {"id": "F3", "rule": "Same delivery entered twice", "needs": ["materials"], "runnable": False},
            ]}
