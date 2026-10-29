"""Join the takeoff with the bill. Every line gets exactly one status and a reason.

Statuses: matched (equals a measured item), different (a measured item disagrees),
blocked (a measured item has a missing input), printed (the quantity is printed on a
drawing of the same building), derived (repeats or converts another checked line),
review (only weak candidates), not_found.
"""
import re
from collections import Counter, defaultdict

from .. import rules as R
from .. import runlog, store
from ..text.normalise import fold_key
from .evidence import Finder, source_of

REPEAT_WORDS = re.compile(r"əlavə|hər növbəti|her novbeti|növbəti gediş|qalınlığın hər|dəyişdikdə|dəyişməsi")
DENSITIES = (1.2, 1.5, 1.6, 1.75, 1.8, 1.95, 2.0, 2.4, 2.5)
CHECKED = {"matched", "printed", "derived"}


def _close(a: float, b: float, decimals: int = 3) -> bool:
    return abs(a - b) <= max(10 ** -decimals / 2, 1e-9) + 1e-9 * max(abs(a), abs(b))


def _reviewer(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)", comment)
    if m:
        return {"text": comment, "kind": "difference", "value": float(m.group(3).replace(",", ".")),
                "explain": f"reviewer computes {m.group(1)} − {m.group(2)} = {m.group(3)}"}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(m2|m3|m²|m³)\s*az", comment)
    if m:
        return {"text": comment, "kind": "reduce", "delta": -float(m.group(1).replace(",", ".")),
                "explain": f"reviewer says {m.group(1)} {m.group(2)} less should be given"}
    return {"text": comment, "kind": "note"}


def run_match() -> dict:
    bill, take = store.get("bill"), store.get("takeoff")
    items = {i["id"]: i for i in take["items"]}
    lines = bill["lines"]
    by_id = {l["id"]: l for l in lines}
    out: dict[str, dict] = {}
    linked_items = set()
    with runlog.stage("match"):
        for bm in R.load("bill_map"):
            item = items.get(bm["item"])
            if item is None:
                runlog.warn("match", f"{bm['id']}: item {bm['item']} does not exist")
                continue
            linked_items.add(item["id"])
            v = item["value"]
            present = [by_id[x] for x in bm["lines"] if x in by_id]
            if v["status"] == "blocked":
                for l in present:
                    out[l["id"]] = {"status": "blocked", "item": item["id"], "our_qty": None,
                                    "reason": f"{item['label_en']} is blocked: missing {', '.join(v['missing']) or 'input'}",
                                    "method": v["method"], "link": bm["id"], "item_status": v["status"]}
                continue
            if bm["relation"] == "sum":
                total = sum(l["qty"] for l in present)
                same = _close(total, v["value"], 1)
                for l in present:
                    out[l["id"]] = {"status": "matched" if same else "different", "item": item["id"],
                                    "our_qty": v["value"], "group_total": total, "link": bm["id"],
                                    "reason": (f"lines {' + '.join(x['id'] for x in present)} = {total:g} "
                                               f"{'equals' if same else 'differs from'} the printed {v['value']:g} {v['unit']}"),
                                    "method": v["method"], "item_status": v["status"]}
                continue
            for l in present:
                same = _close(l["qty"], v["value"], 3)
                gap = l["qty"] - v["value"]
                out[l["id"]] = {"status": "matched" if same else "different", "item": item["id"], "our_qty": v["value"],
                                "gap": None if same else gap, "gap_pct": None if same else (gap / v["value"] * 100 if v["value"] else None),
                                "reason": (f"equals {item['label_en']}" if same else
                                           f"bill {l['qty']:g} vs drawing {v['value']:g} {v['unit']}"),
                                "method": v["method"], "link": bm["id"], "item_status": v["status"]}
        # Measured items that equal a bill line of the same building, found automatically.
        for item in take["items"]:
            v = item["value"]
            if v["status"] == "blocked" or item["id"] in linked_items:
                continue
            for l in lines:
                if l["id"] in out or l["unit"] != item["unit"]:
                    continue
                from .evidence import BUILDING_OK
                if item["building"] not in BUILDING_OK.get(l["building"], {l["building"]}) and \
                        not (l["building"] == "site" and item["building"] == "site"):
                    continue
                if _close(l["qty"], v["value"], 3):
                    out[l["id"]] = {"status": "matched", "item": item["id"], "our_qty": v["value"],
                                    "reason": f"equals {item['label_en']} (found automatically)", "method": v["method"],
                                    "item_status": v["status"]}
                    linked_items.add(item["id"])
        finder = Finder()
        section_regions = defaultdict(set)
        for l in lines:
            if l["id"] in out:
                continue
            strong, weak = finder.direct(l["qty"], l["unit"], l["building"], l["description"])
            if strong:
                e = strong[0]
                why = (f"next to the words {', '.join(e['overlap'][:3])}" if e["overlap"] else f"written with its unit {l['unit']}")
                out[l["id"]] = {"status": "printed", "our_qty": l["qty"], "method": "stated",
                                "reason": f"{l['qty']:g} {l['unit']} is printed on {e['file'].split('/')[-1]}"
                                          f"{' sheet ' + e['sheet'] if e.get('sheet') else ''}, {why}",
                                "sources": [source_of(x) for x in strong[:4]]}
                for x in strong[:4]:
                    section_regions[l["section"]].add((x["file_id"], x.get("region") or x.get("page")))
                continue
            out[l["id"]] = {"status": "pending", "weak": [source_of(e) for e in weak[:3]]}
        for l in lines:
            for s in (out[l["id"]].get("sources") or []):
                loc = s.get("locator", {})
                section_regions[l["section"]].add((s.get("file_id"), loc.get("region") or loc.get("page")))
        _derived(lines, out)
        for l in lines:
            r = out[l["id"]]
            if r["status"] != "pending":
                continue
            if l["unit"] in ("m³", "m²", "t", "m") and l["qty"] >= 10 and section_regions.get(l["section"]):
                pair = finder.pair(l["qty"], section_regions[l["section"]], l["unit"], l["description"])
                if pair:
                    p = pair[0]
                    out[l["id"]] = {"status": "printed", "our_qty": l["qty"], "method": "derived",
                                    "reason": f"{p['a']['value']:g} {p['op']} {p['b']['value']:g} = {l['qty']:g}, both printed on "
                                              f"{p['a']['file'].split('/')[-1]}",
                                    "sources": [source_of(p["a"]), source_of(p["b"])]}
                    continue
            if r.get("weak"):
                out[l["id"]] = {"status": "review", "our_qty": None, "candidates": r["weak"],
                                "reason": "only weak candidates: the number appears on a drawing of this building "
                                          "without a unit or with too few digits"}
            else:
                out[l["id"]] = {"status": "not_found", "our_qty": None,
                                "reason": "no measured item and the quantity is not printed on any drawing of this building"}
        _derived(lines, out)
        for l in lines:
            adj = _reviewer(l.get("comment"))
            if adj:
                out[l["id"]]["reviewer"] = adj
                if adj.get("kind") == "reduce":
                    adj["value"] = l["qty"] + adj["delta"]
        report = _summarise(bill, take, out, linked_items)
    return report


def _derived(lines, out):
    """Repeats ('əlavə', 'each next pass') and tonnes from m³ inherit the checked parent line."""
    by_section = defaultdict(list)
    for l in lines:
        by_section[l["section"]].append(l)
    for sec_lines in by_section.values():
        for i, l in enumerate(sec_lines):
            r = out.get(l["id"], {})
            if r.get("status") not in (None, "pending", "not_found", "review"):
                continue
            for parent in reversed(sec_lines[:i]):
                pr = out.get(parent["id"], {})
                if pr.get("status") not in CHECKED:
                    continue
                if parent["unit"] == l["unit"] and _close(parent["qty"], l["qty"], 3):
                    kind = "repeat" if REPEAT_WORDS.search(l["description"]) else "same quantity"
                    out[l["id"]] = {"status": "derived", "derived_from": parent["id"], "our_qty": parent.get("our_qty") or parent["qty"],
                                    "kind": kind, "method": "derived",
                                    "reason": f"{'repeats' if kind == 'repeat' else 'same quantity as'} line {parent['id']} "
                                              f"({parent['qty']:g} {parent['unit']})"}
                    break
                if l["unit"] == "t" and parent["unit"] == "m³" and parent["qty"]:
                    ratio = round(l["qty"] / parent["qty"], 3)
                    if any(abs(ratio - d) < 1e-6 for d in DENSITIES):
                        out[l["id"]] = {"status": "derived", "derived_from": parent["id"], "our_qty": l["qty"],
                                        "kind": "density", "density": ratio, "method": "derived",
                                        "reason": f"{parent['qty']:g} m³ × {ratio:g} t/m³ from line {parent['id']}; the "
                                                  f"density is the estimator's choice, not on a drawing"}
                        break


def _summarise(bill, take, out, linked_items) -> dict:
    lines = bill["lines"]
    counts = Counter(r["status"] for r in out.values())
    value = defaultdict(float)
    for l in lines:
        value[out[l["id"]]["status"]] += l["amount"] or 0.0
    by_building = defaultdict(lambda: {"value": 0.0, "checked": 0.0, "lines": 0, "checked_lines": 0})
    for l in lines:
        b = by_building[l["building"]]
        b["value"] += l["amount"] or 0.0
        b["lines"] += 1
        if out[l["id"]]["status"] in CHECKED | {"different"}:
            b["checked"] += l["amount"] or 0.0
            b["checked_lines"] += 1
    value_by_building = sorted(({"building": k, **v} for k, v in by_building.items()), key=lambda r: -r["value"])
    lists = {"matched": [], "different": [], "not_found": [], "blocked": [], "review": []}
    for l in lines:
        r = out[l["id"]]
        row = {"id": l["id"], "description": l["description"], "unit": l["unit"], "bill_qty": l["qty"],
               "our_qty": r.get("our_qty"), "gap": r.get("gap"), "gap_pct": r.get("gap_pct"), "status": r["status"],
               "reason": r["reason"], "amount": l["amount"], "building": l["building"], "row": l["row"]}
        if r["status"] in CHECKED:
            lists["matched"].append(row)
        elif r["status"] in lists:
            lists[r["status"]].append(row)
    items_unlinked = [i for i in take["items"] if i["id"] not in linked_items and i["value"]["status"] != "blocked"]
    attention = []
    for i in take["items"]:
        if i["value"]["status"] == "blocked":
            attention.append({"kind": "blocked", "id": i["id"], "label": i["label_en"], "label_az": i["label_az"],
                              "detail": i["value"]["note"] or "missing " + ", ".join(i["value"]["missing"])})
        elif i["value"]["conflicts"]:
            attention.append({"kind": "conflict", "id": i["id"], "label": i["label_en"], "label_az": i["label_az"],
                              "detail": i["value"]["note"]})
    for row in sorted(lists["different"], key=lambda r: -abs((r["gap"] or 0) * ((r["amount"] or 0) / (r["bill_qty"] or 1)))):
        attention.append({"kind": "different", "id": row["id"], "label": row["description"][:90], "label_az": row["description"],
                          "detail": row["reason"]})
    runlog.event("match", "info", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return {"lines": out, "counts": dict(counts), "value_by_status": {k: round(v, 2) for k, v in value.items()},
            "lists": lists, "value_by_building": value_by_building, "measured_no_bill_line": items_unlinked,
            "attention": attention[:30], "total_value": round(sum(l["amount"] or 0 for l in lines), 2)}
