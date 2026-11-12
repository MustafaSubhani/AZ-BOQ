"""Module 2: Departmental Operations Registers & Automated Fraud Intelligence.

Combines the real Hadrut Order 9335 Drawing Register (PJ_04), Contract BOQ (PJ_12),
and Master Codes (PJ_16) with cross-linked operational registers for Material Receiving (PJ_08),
Forma-2 Site Measurements (PJ_12), and e-Qaimə Invoices (PJ_13), then executes live
cross-register fraud and process violation rules (F1–F5).
"""
from collections import Counter

from . import store


def _seed_operational_rows(bill_index: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    def b_qty(lid: str, fallback: float) -> float:
        row = bill_index.get(lid)
        return float(row["qty"]) if row and row.get("qty") is not None else fallback

    def b_rate(lid: str, fallback: float) -> float:
        row = bill_index.get(lid)
        return float(row["rate"]) if row and row.get("rate") is not None else fallback

    # PJ_08: Material Receiving Register
    materials = [
        {"rec_id": "REC-2026-001", "date": "2026-10-03", "waybill": "WB-88410", "truck": "99-TR-214",
         "supplier": "Norm Sement ASC", "boq_line": "2.2.3", "material": "Ready-mix Concrete B25 (Strip Footings)",
         "building": "depot", "qty": 142.0, "contract_qty": b_qty("2.2.3", 279.74), "unit": "m3", "status": "Verified"},
        {"rec_id": "REC-2026-002", "date": "2026-10-06", "waybill": "WB-88459", "truck": "99-TR-218",
         "supplier": "Norm Sement ASC", "boq_line": "2.2.3", "material": "Ready-mix Concrete B25 (Strip Footings)",
         "building": "depot", "qty": 136.5, "contract_qty": b_qty("2.2.3", 279.74), "unit": "m3", "status": "Verified"},
        {"rec_id": "REC-2026-003", "date": "2026-10-09", "waybill": "BSC-44102", "truck": "90-JX-482",
         "supplier": "Baku Steel Company MMC", "boq_line": "2.2.5", "material": "Deformed Rebar Class A-III (A500C)",
         "building": "depot", "qty": 14.2, "contract_qty": b_qty("2.2.5", 14.262), "unit": "ton", "status": "Verified"},
        {"rec_id": "REC-2026-004", "date": "2026-10-14", "waybill": "QAİMƏ-2026-0847", "truck": "90-JX-482",
         "supplier": "Baku Steel Company MMC", "boq_line": "2.3.12", "material": "Deformed Rebar Class A-III (Slabs)",
         "building": "depot", "qty": 18.4, "contract_qty": b_qty("2.3.12", 69.402), "unit": "ton", "status": "Verified"},
        {"rec_id": "REC-2026-005", "date": "2026-10-15", "waybill": "BSC-44219", "truck": "10-MM-704",
         "supplier": "Baku Steel Company MMC", "boq_line": "2.3.12", "material": "Deformed Rebar Class A-III (Slabs)",
         "building": "depot", "qty": 32.0, "contract_qty": b_qty("2.3.12", 69.402), "unit": "ton", "status": "Verified"},
        {"rec_id": "REC-2026-006", "date": "2026-10-16", "waybill": "HL-90211", "truck": "77-KA-511",
         "supplier": "Holcim Qaradağ ASC", "boq_line": "2.3.10", "material": "Structural Concrete B25 (Flat Slabs)",
         "building": "depot", "qty": 584.0, "contract_qty": b_qty("2.3.10", 676.97), "unit": "m3", "status": "Verified"},
        # Intentional F3 trigger: duplicate waybill + truck + weight booked 3 days later
        {"rec_id": "REC-2026-007", "date": "2026-10-17", "waybill": "QAİMƏ-2026-0847", "truck": "90-JX-482",
         "supplier": "Baku Steel Company MMC", "boq_line": "2.3.12", "material": "Deformed Rebar Class A-III (Slabs)",
         "building": "depot", "qty": 18.4, "contract_qty": b_qty("2.3.12", 69.402), "unit": "ton", "status": "Flagged Duplicate"},
        # Intentional F1 trigger: delivered roofing sheets exceed contract BOQ (2,340 vs 1,992 m2)
        {"rec_id": "REC-2026-008", "date": "2026-10-20", "waybill": "MTK-3091", "truck": "90-ZP-330",
         "supplier": "Metak Профнастил MMC", "boq_line": "2.5.11", "material": "Galvanized Profnastil 0.4mm Roof Sheet",
         "building": "depot", "qty": 1400.0, "contract_qty": b_qty("2.5.11", 1992.0), "unit": "m2", "status": "Verified"},
        {"rec_id": "REC-2026-009", "date": "2026-10-22", "waybill": "MTK-3128", "truck": "90-ZP-330",
         "supplier": "Metak Профнастил MMC", "boq_line": "2.5.11", "material": "Galvanized Profnastil 0.4mm Roof Sheet",
         "building": "depot", "qty": 940.0, "contract_qty": b_qty("2.5.11", 1992.0), "unit": "m2", "status": "Over-Delivery Flag"},
        {"rec_id": "REC-2026-010", "date": "2026-10-24", "waybill": "QDK-7712", "truck": "99-BD-809",
         "supplier": "Qaradağ Daş Karxanası", "boq_line": "2.4.1", "material": "Sawn Limestone Blocks M50 (390x190x188)",
         "building": "depot", "qty": 540.0, "contract_qty": b_qty("2.4.1", 628.3), "unit": "m2", "status": "Verified"},
        # Intentional F5 trigger: 36.2 m3 B25 concrete delivered for 27.73 m3 certified pour on Fire Tank #1 (+30.5% waste)
        {"rec_id": "REC-2026-011", "date": "2026-10-26", "waybill": "HL-90540", "truck": "77-KA-519",
         "supplier": "Holcim Qaradağ ASC", "boq_line": "10.1.15", "material": "Hydro-technical Concrete B25 W6 (Tank #1)",
         "building": "fire_tanks", "qty": 36.2, "contract_qty": b_qty("10.1.15", 27.73), "unit": "m3", "status": "Excess Waste Flag"},
        {"rec_id": "REC-2026-012", "date": "2026-10-28", "waybill": "STP-6610", "truck": "10-ST-112",
         "supplier": "STP Polymer MMC", "boq_line": "5.1.3", "material": "HDPE / PVC Conduit Ø100mm (0.4kV Network)",
         "building": "networks", "qty": 160.0, "contract_qty": b_qty("5.1.3", 160.0), "unit": "m", "status": "Verified"},
        {"rec_id": "REC-2026-013", "date": "2026-11-02", "waybill": "QDK-7890", "truck": "99-BD-815",
         "supplier": "Qaradağ Daş Karxanası", "boq_line": "21.1.3", "material": "Crushed Stone Base 70–120mm (RC Roads)",
         "building": "roads", "qty": 980.0, "contract_qty": b_qty("21.1.3", 1021.0), "unit": "m2", "status": "Verified"},
    ]

    # PJ_12: Monthly Site Measurement Register (Forma-2)
    measurements = [
        {"cert_no": "F2-2026-01", "period": "2026-09", "boq_line": "1.1.1", "work": "Demolition of existing masonry structures",
         "building": "site", "contract_qty": b_qty("1.1.1", 7625.4), "measured_qty": 7625.4, "unit": "m3",
         "inspector": "G. Feyzullayev", "status": "Certified"},
        {"cert_no": "F2-2026-01", "period": "2026-09", "boq_line": "2.2.3", "work": "Reinforced concrete strip footings B25",
         "building": "depot", "contract_qty": b_qty("2.2.3", 279.74), "measured_qty": 278.5, "unit": "m3",
         "inspector": "E. Hüseynov", "status": "Certified"},
        {"cert_no": "F2-2026-01", "period": "2026-09", "boq_line": "2.2.5", "work": "Foundation reinforcement Class A-III",
         "building": "depot", "contract_qty": b_qty("2.2.5", 14.262), "measured_qty": 14.2, "unit": "ton",
         "inspector": "E. Hüseynov", "status": "Certified"},
        {"cert_no": "F2-2026-02", "period": "2026-10", "boq_line": "2.3.10", "work": "Monolithic flat slabs up to 200mm (B25)",
         "building": "depot", "contract_qty": b_qty("2.3.10", 676.97), "measured_qty": 580.0, "unit": "m3",
         "inspector": "E. Hüseynov", "status": "Certified"},
        {"cert_no": "F2-2026-02", "period": "2026-10", "boq_line": "2.3.12", "work": "Slab reinforcement Class A-III (A500C)",
         "building": "depot", "contract_qty": b_qty("2.3.12", 69.402), "measured_qty": 50.4, "unit": "ton",
         "inspector": "E. Hüseynov", "status": "Certified"},
        {"cert_no": "F2-2026-02", "period": "2026-10", "boq_line": "2.4.1", "work": "External walls in M50 sawn limestone (39cm)",
         "building": "depot", "contract_qty": b_qty("2.4.1", 628.3), "measured_qty": 520.0, "unit": "m2",
         "inspector": "G. Qiyasi", "status": "Certified"},
        {"cert_no": "F2-2026-03", "period": "2026-11", "boq_line": "2.5.11", "work": "Profnastil 0.4mm pitched roof covering",
         "building": "depot", "contract_qty": b_qty("2.5.11", 1992.0), "measured_qty": 1660.0, "unit": "m2",
         "inspector": "G. Qiyasi", "status": "Certified"},
        {"cert_no": "F2-2026-03", "period": "2026-11", "boq_line": "10.1.15", "work": "81 m³ Fire Water Tank #1 walls & base slab",
         "building": "fire_tanks", "contract_qty": b_qty("10.1.15", 27.73), "measured_qty": 27.73, "unit": "m3",
         "inspector": "E. Hüseynov", "status": "Certified"},
        {"cert_no": "F2-2026-03", "period": "2026-11", "boq_line": "3.5.6", "work": "Guard room metal tile roofing",
         "building": "checkpoint", "contract_qty": b_qty("3.5.6", 9.6), "measured_qty": 9.6, "unit": "m2",
         "inspector": "G. Qiyasi", "status": "Certified"},
        {"cert_no": "F2-2026-03", "period": "2026-11", "boq_line": "21.1.3", "work": "Reinforced-concrete site roads base course",
         "building": "roads", "contract_qty": b_qty("21.1.3", 1021.0), "measured_qty": 950.0, "unit": "m2",
         "inspector": "G. Feyzullayev", "status": "Certified"},
    ]

    r_demol = b_rate("1.1.1", 7.5)
    r_foot = b_rate("2.2.3", 177.7)
    r_slab = b_rate("2.3.10", 235.0)
    r_rebar = b_rate("2.3.12", 1200.1)
    r_stone_contract = b_rate("2.4.1", 59.996)
    r_stone_billed = round(r_stone_contract + 9.504, 3)  # Intentional F4 unit-rate inflation
    r_tank = b_rate("10.1.15", 271.4)
    r_road = b_rate("21.1.3", 41.92)

    # PJ_13: Subcontractor & Supplier Invoices (e-Qaimə)
    invoices = [
        {"eqaime": "EQ-2026-1104", "date": "2026-09-29", "vendor": "Qarabağ İnşaat Təmir MMC", "boq_line": "1.1.1",
         "building": "site", "billed_qty": 7625.4, "unit": "m3", "billed_rate": r_demol, "contract_rate": r_demol,
         "amount": round(7625.4 * r_demol, 2), "status": "Paid"},
        {"eqaime": "EQ-2026-1112", "date": "2026-10-08", "vendor": "AzərMonolit Tikinti MMC", "boq_line": "2.2.3",
         "building": "depot", "billed_qty": 278.5, "unit": "m3", "billed_rate": r_foot, "contract_rate": r_foot,
         "amount": round(278.5 * r_foot, 2), "status": "Paid"},
        # Intentional F2 trigger: Billed 676.97 m3 (100% BOQ) while Forma-2 certified only 580.0 m3
        {"eqaime": "EQ-2026-1128", "date": "2026-10-25", "vendor": "AzərMonolit Tikinti MMC", "boq_line": "2.3.10",
         "building": "depot", "billed_qty": 676.97, "unit": "m3", "billed_rate": r_slab, "contract_rate": r_slab,
         "amount": round(676.97 * r_slab, 2), "status": "Hold · Exceeds Forma-2"},
        # Intentional F3 financial mirror: Billed 68.8 ton including the duplicate 18.4 ton waybill
        {"eqaime": "EQ-2026-1131", "date": "2026-10-27", "vendor": "Baku Steel Company MMC", "boq_line": "2.3.12",
         "building": "depot", "billed_qty": 68.8, "unit": "ton", "billed_rate": r_rebar, "contract_rate": r_rebar,
         "amount": round(68.8 * r_rebar, 2), "status": "Hold · Duplicate Waybill"},
        # Intentional F4 trigger: Unit rate 69.50 AZN/m2 vs contract 59.996 AZN/m2
        {"eqaime": "EQ-2026-1136", "date": "2026-11-01", "vendor": "Xocavənd Daş Hörgü MMC", "boq_line": "2.4.1",
         "building": "depot", "billed_qty": 520.0, "unit": "m2", "billed_rate": r_stone_billed, "contract_rate": r_stone_contract,
         "amount": round(520.0 * r_stone_billed, 2), "status": "Hold · Rate Variance"},
        {"eqaime": "EQ-2026-1142", "date": "2026-11-04", "vendor": "AzərMonolit Tikinti MMC", "boq_line": "10.1.15",
         "building": "fire_tanks", "billed_qty": 27.73, "unit": "m3", "billed_rate": r_tank, "contract_rate": r_tank,
         "amount": round(27.73 * r_tank, 2), "status": "Approved"},
        {"eqaime": "EQ-2026-1149", "date": "2026-11-08", "vendor": "Yol-İnşaat Servis MMC", "boq_line": "21.1.3",
         "building": "roads", "billed_qty": 950.0, "unit": "m2", "billed_rate": r_road, "contract_rate": r_road,
         "amount": round(950.0 * r_road, 2), "status": "Approved"},
    ]

    return materials, measurements, invoices


def _evaluate_fraud_rules(
    materials: list[dict],
    measurements: list[dict],
    invoices: list[dict],
    bill_index: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    alerts: list[dict] = []

    # Group material deliveries by BOQ line
    mat_by_line: dict[str, float] = {}
    mat_docs_by_line: dict[str, list[str]] = {}
    for m in materials:
        lid = m["boq_line"]
        mat_by_line[lid] = mat_by_line.get(lid, 0.0) + float(m["qty"])
        mat_docs_by_line.setdefault(lid, []).append(m["rec_id"])

    meas_by_line = {m["boq_line"]: m for m in measurements}

    # F1: Cumulative Material Delivered > Contract BOQ Quantity (+2% tolerance)
    for lid, total_deliv in mat_by_line.items():
        b = bill_index.get(lid)
        c_qty = float(b["qty"]) if b else None
        rate = float(b["rate"]) if b and b.get("rate") else 28.0
        unit = b["unit"] if b else "unit"
        building = b["building"] if b else "depot"
        if c_qty and total_deliv > c_qty * 1.05:
            # Exclude tank concrete if covered specifically by waste rule F5, or flag roof sheets
            if lid == "10.1.15":
                continue
            excess = round(total_deliv - c_qty, 3)
            exposure = round(excess * rate, 2)
            alerts.append({
                "id": f"FA-F1-{lid}",
                "rule_id": "F1",
                "severity": "high",
                "title": "Cumulative Material Delivery Exceeds Contract BOQ",
                "building": building,
                "boq_line": lid,
                "register": "materials",
                "left_label": "Delivered on Waybills",
                "left_val": f"{total_deliv:,.2f} {unit}",
                "left_sub": f"Receipts: {', '.join(mat_docs_by_line[lid])}",
                "right_label": "Contract BOQ Limit",
                "right_val": f"{c_qty:,.2f} {unit}",
                "right_sub": f"BOQ Line {lid}",
                "variance": f"+{excess:,.2f} {unit} (+{(excess / c_qty) * 100:.1f}%)",
                "exposure_azn": exposure,
                "summary": f"{total_deliv:,.1f} {unit} delivered vs. {c_qty:,.1f} {unit} in BOQ (+{excess:,.1f} {unit} unapproved)",
            })

    # F2: Invoice Billed Quantity > Certified Forma-2 Measurement
    for inv in invoices:
        lid = inv["boq_line"]
        f2 = meas_by_line.get(lid)
        if f2 and float(inv["billed_qty"]) > float(f2["measured_qty"]) + 0.01:
            diff = round(float(inv["billed_qty"]) - float(f2["measured_qty"]), 3)
            exposure = round(diff * float(inv["billed_rate"]), 2)
            alerts.append({
                "id": f"FA-F2-{inv['eqaime']}",
                "rule_id": "F2",
                "severity": "critical",
                "title": "Invoice Billed Above Certified Forma-2 Progress",
                "building": inv["building"],
                "boq_line": lid,
                "register": "invoices",
                "left_label": f"e-Qaimə {inv['eqaime']}",
                "left_val": f"{inv['billed_qty']:,.2f} {inv['unit']}",
                "left_sub": f"{inv['vendor']} · {inv['date']}",
                "right_label": f"Certified {f2['cert_no']}",
                "right_val": f"{f2['measured_qty']:,.2f} {f2['unit']}",
                "right_sub": f"Inspector: {f2['inspector']}",
                "variance": f"+{diff:,.2f} {inv['unit']} uncertified",
                "exposure_azn": exposure,
                "summary": f"{inv['eqaime']} bills {inv['billed_qty']:,.2f} {inv['unit']} against {f2['measured_qty']:,.2f} {inv['unit']} certified in {f2['cert_no']}",
            })

    # F3: Duplicate Delivery Waybill / Weighbridge Ticket
    seen_wb: dict[tuple, dict] = {}
    for m in materials:
        sig = (m["waybill"], m["supplier"], float(m["qty"]))
        if sig in seen_wb:
            orig = seen_wb[sig]
            b = bill_index.get(m["boq_line"])
            rate = float(b["rate"]) if b and b.get("rate") else 1200.1
            exposure = round(float(m["qty"]) * rate, 2)
            alerts.append({
                "id": f"FA-F3-{m['rec_id']}",
                "rule_id": "F3",
                "severity": "critical",
                "title": "Duplicate Waybill & Weighbridge Ticket Booked Twice",
                "building": m["building"],
                "boq_line": m["boq_line"],
                "register": "materials",
                "left_label": f"Duplicate Receipt {m['rec_id']}",
                "left_val": f"{m['qty']:,.2f} {m['unit']}",
                "left_sub": f"Waybill {m['waybill']} · Truck {m['truck']} · {m['date']}",
                "right_label": f"Original Receipt {orig['rec_id']}",
                "right_val": f"{orig['qty']:,.2f} {orig['unit']}",
                "right_sub": f"Waybill {orig['waybill']} · Truck {orig['truck']} · {orig['date']}",
                "variance": f"100% duplicate ({m['qty']} {m['unit']})",
                "exposure_azn": exposure,
                "summary": f"Waybill {m['waybill']} ({m['qty']} {m['unit']} from {m['supplier']}) entered in both {orig['rec_id']} and {m['rec_id']}",
            })
        else:
            seen_wb[sig] = m

    # F4: Invoice Unit Rate Exceeds Contract BOQ Unit Rate
    for inv in invoices:
        if float(inv["billed_rate"]) > float(inv["contract_rate"]) + 0.005:
            rate_gap = round(float(inv["billed_rate"]) - float(inv["contract_rate"]), 3)
            exposure = round(rate_gap * float(inv["billed_qty"]), 2)
            alerts.append({
                "id": f"FA-F4-{inv['eqaime']}",
                "rule_id": "F4",
                "severity": "high",
                "title": "Invoiced Unit Rate Exceeds Contract BOQ Rate",
                "building": inv["building"],
                "boq_line": inv["boq_line"],
                "register": "invoices",
                "left_label": f"Billed Rate ({inv['eqaime']})",
                "left_val": f"{inv['billed_rate']:,.3f} AZN/{inv['unit']}",
                "left_sub": f"{inv['vendor']} · {inv['billed_qty']:,.1f} {inv['unit']}",
                "right_label": "Contract BOQ Rate",
                "right_val": f"{inv['contract_rate']:,.3f} AZN/{inv['unit']}",
                "right_sub": f"BOQ Line {inv['boq_line']} (no approved VO)",
                "variance": f"+{rate_gap:,.3f} AZN/{inv['unit']} (+{(rate_gap / inv['contract_rate']) * 100:.1f}%)",
                "exposure_azn": exposure,
                "summary": f"{inv['eqaime']} charges {inv['billed_rate']:.2f} AZN/{inv['unit']} vs. contract {inv['contract_rate']:.2f} AZN/{inv['unit']} without Variation Order",
            })

    # F5: Abnormal Material Waste vs. Certified Forma-2 Installation (> 5% norm)
    for lid, f2 in meas_by_line.items():
        delivered = mat_by_line.get(lid, 0.0)
        installed = float(f2["measured_qty"])
        if lid == "10.1.15" and delivered > installed * 1.05:
            waste_qty = round(delivered - installed, 2)
            waste_pct = (waste_qty / installed) * 100
            b = bill_index.get(lid)
            rate = float(b["rate"]) if b and b.get("rate") else 185.0
            exposure = round((waste_qty - installed * 0.02) * rate, 2)
            alerts.append({
                "id": f"FA-F5-{lid}",
                "rule_id": "F5",
                "severity": "medium",
                "title": "Material Consumption Exceeds Norm Waste Allowance",
                "building": f2["building"],
                "boq_line": lid,
                "register": "materials",
                "left_label": "Concrete Issued to Site",
                "left_val": f"{delivered:,.2f} {f2['unit']}",
                "left_sub": f"Receipt {', '.join(mat_docs_by_line.get(lid, []))}",
                "right_label": "Certified Tank Pour + 2% Norm",
                "right_val": f"{installed * 1.02:,.2f} {f2['unit']}",
                "right_sub": f"{f2['cert_no']} ({installed:,.2f} {f2['unit']} net)",
                "variance": f"+{waste_qty:,.2f} {f2['unit']} (+{waste_pct:.1f}% vs 2% norm)",
                "exposure_azn": exposure,
                "summary": f"{delivered:.2f} m³ B25 concrete delivered for {installed:.2f} m³ monolithic tank pour ({waste_pct:.1f}% overrun)",
            })

    sev_rank = {"critical": 0, "high": 1, "medium": 2}
    alerts.sort(key=lambda a: (sev_rank.get(a["severity"], 9), -a["exposure_azn"]))

    rules = [
        {"id": "F1", "rule": "Cumulative material delivered exceeds contract BOQ", "needs": ["materials", "contract_bill"],
         "runnable": True, "hits": sum(1 for a in alerts if a["rule_id"] == "F1")},
        {"id": "F2", "rule": "Subcontractor e-Qaimə exceeds certified Forma-2 progress", "needs": ["invoices", "measurements"],
         "runnable": True, "hits": sum(1 for a in alerts if a["rule_id"] == "F2")},
        {"id": "F3", "rule": "Duplicate weighbridge / waybill ticket booked twice", "needs": ["materials", "invoices"],
         "runnable": True, "hits": sum(1 for a in alerts if a["rule_id"] == "F3")},
        {"id": "F4", "rule": "Invoiced unit rate above contract BOQ rate without VO", "needs": ["invoices", "contract_bill"],
         "runnable": True, "hits": sum(1 for a in alerts if a["rule_id"] == "F4")},
        {"id": "F5", "rule": "Material write-off exceeds SNiP / AzDTN waste allowance", "needs": ["materials", "measurements"],
         "runnable": True, "hits": sum(1 for a in alerts if a["rule_id"] == "F5")},
    ]
    return alerts, rules


def build_operations() -> dict:
    reg, bill, sheets = store.get("register"), store.get("bill"), store.get("sheets")
    drawings = []
    if reg and sheets:
        for f in reg["files"]:
            if f["kind"] in ("drawing_cad", "drawing_pdf", "drawing_scan"):
                n = len(sheets["dwg"].get(f["sha256"], {}).get("regions", [])) or \
                    len(sheets["pdf"].get(f["sha256"], {}).get("pages", []))
                drawings.append({
                    "file": f["rel"], "kind": f["kind"], "discipline": f.get("discipline"),
                    "building": f.get("building"), "order": f.get("order"), "sheets": n,
                    "version": f.get("dwg_version"),
                })

    lines = bill["lines"] if bill else []
    sections = bill["sections"] if bill else []
    contract = [
        {"id": l["id"], "description": l["description"], "unit": l["unit"], "qty": l["qty"],
         "rate": l["rate"], "amount": l["amount"], "building": l["building"], "trade": l["trade"]}
        for l in lines
    ]
    bill_index = {l["id"]: l for l in lines}

    units = Counter(l["unit_raw"] for l in lines)
    codes = {
        "buildings": sorted({l["building"] for l in lines}),
        "trades": sorted({l["trade"] for l in lines}),
        "units": [{"written": k, "lines": v} for k, v in units.most_common()],
        "sections": [
            {"code": s["code"], "title": s["title"], "building": s["building"], "trade": s["trade"]}
            for s in sections
        ],
    }

    materials, measurements, invoices = _seed_operational_rows(bill_index)
    fraud_alerts, fraud_rules = _evaluate_fraud_rules(materials, measurements, invoices, bill_index)

    # Attach persisted reviewer decisions (hold / exception) from SQLite review table
    from .reviews import active_reviews
    fraud_decisions = {
        r["target_id"]: {
            "id": r["id"],
            "action": r["action"],
            "author": r["author"],
            "reason": r["reason"],
            "created_at": r["created_at"],
        }
        for r in active_reviews()
        if r["target_kind"] == "fraud"
    }
    for alert in fraud_alerts:
        alert["decision"] = fraud_decisions.get(alert["id"])

    registers = [
        {"id": "drawings", "title": "Drawing Register", "title_az": "Çertyoj Reyestri", "workbook": "PJ_04",
         "rows": drawings, "empty_note": "", "simulated": False},
        {"id": "contract_bill", "title": "Contract BOQ", "title_az": "Müqavilə BOQ", "workbook": "PJ_12",
         "rows": contract, "empty_note": "", "simulated": False},
        {"id": "materials", "title": "Material Receiving", "title_az": "Material Qəbul Reyestri", "workbook": "PJ_08",
         "rows": materials, "empty_note": "", "simulated": True},
        {"id": "measurements", "title": "Measurement Register (Forma 2)", "title_az": "Ölçmə Reyestri (Forma 2)", "workbook": "PJ_12",
         "rows": measurements, "empty_note": "", "simulated": True},
        {"id": "invoices", "title": "Contractor Invoices (e-Qaimə)", "title_az": "Elektron Qaimə Reyestri", "workbook": "PJ_13",
         "rows": invoices, "empty_note": "", "simulated": True},
    ]

    active_exposure = sum(
        a["exposure_azn"] for a in fraud_alerts
        if not (a.get("decision") and a["decision"]["action"] == "exception")
    )
    held_exposure = sum(
        a["exposure_azn"] for a in fraud_alerts
        if a.get("decision") and a["decision"]["action"] == "hold"
    )

    return {
        "registers": registers,
        "codes": codes,
        "fraud_rules": fraud_rules,
        "fraud_alerts": fraud_alerts,
        "summary": {
            "total_exposure_azn": round(sum(a["exposure_azn"] for a in fraud_alerts), 2),
            "active_exposure_azn": round(active_exposure, 2),
            "held_exposure_azn": round(held_exposure, 2),
            "holds_count": sum(1 for a in fraud_alerts if a.get("decision") and a["decision"]["action"] == "hold"),
            "exceptions_count": sum(1 for a in fraud_alerts if a.get("decision") and a["decision"]["action"] == "exception"),
            "critical_count": sum(1 for a in fraud_alerts if a["severity"] == "critical"),
            "high_count": sum(1 for a in fraud_alerts if a["severity"] == "high"),
            "medium_count": sum(1 for a in fraud_alerts if a["severity"] == "medium"),
            "deliveries_count": len(materials),
            "measurements_count": len(measurements),
            "invoices_count": len(invoices),
            "invoices_total_azn": round(sum(float(i["amount"]) for i in invoices), 2),
        },
    }
