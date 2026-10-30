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
from ..floors import classify
from ..groups import buildup_groups, close_qty
from ..schedules.conflicts import same_room_conflicts
from ..text.normalise import fold_key
from .elements import classify as element_of_line
from .elements import classify_rule
from .evidence import Finder, source_of, subject_class
from .stated import stated_quantity

REPEAT_WORDS = re.compile(r"əlavə|hər növbəti|her novbeti|növbəti gediş|qalınlığın hər|dəyişdikdə|dəyişməsi")
DENSITIES = (1.2, 1.5, 1.6, 1.75, 1.8, 1.95, 2.0, 2.4, 2.5)
CHECKED = {"matched", "printed", "derived"}


def bill_decimals(q: float) -> int:
    s = f"{q:.6f}".rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def close_at(a: float, b: float, decimals: int) -> bool:
    return abs(a - b) <= 0.5 * 10 ** -decimals + 1e-9


def tolerance_for(method: str, bill_qty: float, ours: float) -> tuple[str, bool]:
    """Schedule and stated values match at the bill's own decimals. Geometry matches within 1%."""
    if method in ("schedule", "stated", "derived", "rule", "manual"):
        d = bill_decimals(bill_qty)
        return f"exact at {d} decimals", close_at(bill_qty, ours, d)
    if method == "geometry":
        return "1%", abs(bill_qty - ours) <= 0.01 * abs(ours) + 1e-9
    return "not auto-matched", False


def _round_bill(q: float, like: float) -> float:
    return round(q, bill_decimals(like))


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
                if v["method"] == "geometry":
                    tol, same = tolerance_for("geometry", total, v["value"])
                else:
                    dec = max(bill_decimals(l["qty"]) for l in present)
                    same = close_at(total, v["value"], dec)
                    tol = f"exact at {dec} decimals"
                group = {"lines": [x["id"] for x in present], "bill_total": total, "drawing_total": v["value"],
                         "gap": None if same else total - v["value"]}
                for l in present:
                    # A matching group confirms each line's own quantity. A differing group does not say how to split it.
                    out[l["id"]] = {"status": "matched" if same else "different", "item": item["id"],
                                    "our_qty": l["qty"] if same else None, "group": group, "link": bm["id"],
                                    "tolerance": tol, "method": v["method"], "item_status": v["status"],
                                    "reason": (f"lines {' + '.join(group['lines'])} = {total:g} "
                                               f"{'equals' if same else 'differs from'} the printed {v['value']:g} {v['unit']}")}
                continue
            for l in present:
                tol, same = tolerance_for(v["method"], l["qty"], v["value"])
                gap = round(l["qty"] - v["value"], 4)
                out[l["id"]] = {"status": "matched" if same else "different", "item": item["id"], "our_qty": v["value"],
                                "gap": None if same else gap, "gap_pct": None if same else (gap / v["value"] * 100 if v["value"] else None),
                                "gap_money": None if same or l.get("rate") is None else gap * l["rate"],
                                "tolerance": tol,
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
                if not auto_match_ok(item, l):
                    continue
                d_src = source_decimals(v)
                decimals = bill_decimals(l["qty"]) if d_src is None else max(bill_decimals(l["qty"]), d_src)
                tol = f"exact at {decimals} decimals"
                out[l["id"]] = {"status": "matched", "item": item["id"], "our_qty": v["value"], "tolerance": tol,
                                "reason": f"equals {item['label_en']} (found automatically)", "method": v["method"],
                                "item_status": v["status"]}
                linked_items.add(item["id"])
        finder = Finder()
        room_conflicts, total_conflicts = _schedule_notes()
        _add_garage_readings(room_conflicts, finder)
        ceramic = _ceramic_walls()
        group_floors = _floors_by_group(lines)
        section_regions = defaultdict(set)
        for l in lines:
            if l["id"] in out:
                continue
            pending = _tile_candidate(l, ceramic)
            if pending:
                out[l["id"]] = pending
                continue
            strong, weak = finder.direct(l["qty"], l["unit"], l["building"], l["description"])
            strong = _on_this_floor(strong, group_floors.get(l["id"]))
            if strong:
                swapped = _subject_swap(l, strong, finder)
                if swapped:
                    out[l["id"]] = swapped
                    continue
                e = strong[0]
                why = (f"next to the words {', '.join(e['overlap'][:3])}" if e["overlap"] else f"written with its unit {l['unit']}")
                printed = e["value"]
                tol, _same = tolerance_for("stated", l["qty"], printed)
                clash = _room_clash(l, printed, room_conflicts)
                if clash:
                    out[l["id"]] = {"status": "review", "our_qty": None, "method": "schedule",
                                    "reason": clash["text"] + "; the bill has " + f"{l['qty']:g}",
                                    "sources": [source_of_cell(a) for a in clash["areas"]]}
                    continue
                out[l["id"]] = {"status": "printed", "our_qty": printed, "method": "stated", "tolerance": tol,
                                "reason": f"{printed:g} {l['unit']} is printed on {e['file'].split('/')[-1]}"
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
            roof = finder.roof_window(l["building"]) if l["unit"] == "each" and "dam pencere" in fold_key(l["description"]) else None
            if roof:
                if close_at(l["qty"], roof["value"], bill_decimals(l["qty"])):
                    out[l["id"]] = {"status": "printed", "our_qty": roof["value"], "method": "stated",
                                    "tolerance": f"exact at {bill_decimals(l['qty'])} decimals",
                                    "reason": f"{roof['value']:g} ədəd is printed for Dam pəncərəsi DP-1 on "
                                              f"{roof['file'].split('/')[-1]}",
                                    "sources": [source_of(roof)]}
                else:
                    gap = l["qty"] - roof["value"]
                    out[l["id"]] = {"status": "different", "our_qty": roof["value"], "method": "stated", "gap": gap,
                                    "reason": f"the drawing prints {roof['value']:g} ədəd for Dam pəncərəsi DP-1; "
                                              f"the bill has {l['qty']:g}",
                                    "sources": [source_of(roof)]}
                continue
            if l["unit"] in ("m³", "m²", "t", "m") and l["qty"] >= 10 and section_regions.get(l["section"]):
                pair = finder.pair(l["qty"], section_regions[l["section"]], l["unit"], l["description"])
                if pair:
                    p = pair[0]
                    av, bv = p["a"]["value"], p["b"]["value"]
                    result = av + bv if p["op"] == "+" else av - bv
                    ours = _round_bill(result, l["qty"])
                    out[l["id"]] = {"status": "printed", "our_qty": ours, "method": "derived",
                                    "tolerance": f"exact at {bill_decimals(l['qty'])} decimals",
                                    "reason": f"{av:g} {p['op']} {bv:g} = {ours:g}, both printed on "
                                              f"{p['a']['file'].split('/')[-1]}",
                                    "sources": [source_of(p["a"]), source_of(p["b"])]}
                    continue
            near = finder.near_schedule(l["qty"], l["unit"], l["building"], l["description"]) if l["qty"] else None
            if near:
                gap = l["qty"] - near["value"]
                out[l["id"]] = {"status": "different", "our_qty": near["value"], "method": "schedule",
                                "gap": gap, "gap_pct": gap / near["value"] * 100 if near["value"] else None,
                                "tolerance": "candidate found within 8%; compared exactly",
                                "reason": f"the schedule prints {near['value']:g} {l['unit']}"
                                          f"{_row_words(near.get('row_label'))}; "
                                          f"the bill has {l['qty']:g}",
                                "sources": [source_of(near)]}
            elif r.get("weak"):
                out[l["id"]] = {"status": "review", "our_qty": None, "candidates": r["weak"],
                                "reason": "only weak candidates: the number appears on a drawing of this building "
                                          "without a unit or with too few digits"}
            else:
                out[l["id"]] = {"status": "not_found", "our_qty": None,
                                "reason": "no measured item and the quantity is not printed on any drawing of this building"}
        _derived(lines, out)
        _propagate_groups(lines, out)
        _coverage_hints(lines, out)
        _volume_hints(lines, out)
        _sheet_counts(lines, out)
        for l in lines:
            adj = _reviewer(l.get("comment"))
            if adj:
                out[l["id"]]["reviewer"] = adj
                if adj.get("kind") == "reduce":
                    adj["value"] = l["qty"] + adj["delta"]
        _note_stated(lines, out, take, finder)
        _apply_decisions(out, take)
        _attach_review_reasons(lines, out, take)
        report = _summarise(bill, take, out, linked_items)
        report["drawing_conflicts"] = finder.note_conflicts() + [
            {"id": c["id"], "text": c["text"]} for c in room_conflicts + total_conflicts]
        from .steel import steel_families
        report["steel"] = steel_families(store.get("register") or {"files": []}, bill)
        _mark_accepted(report)
    return report


def _add_garage_readings(conflicts: list[dict], finder: Finder) -> None:
    """PDF 658.30, DWG text 665.30, and the floor hatch. The line stays in review."""
    target = next((c for c in conflicts if c.get("id") == "room-1-floor_1"), None)
    if target is None:
        return
    finish = target["areas"][1]["value"] if len(target.get("areas") or []) > 1 else None
    sheets = []
    seen = set()
    son = None
    if finish is not None:
        for rows in finder.by_value.values():
            for entry in rows:
                value = entry.get("value")
                if entry.get("kind") != "dxf_text" or value is None or abs(value - finish) > 0.05:
                    continue
                if "qaraj" not in fold_key(entry.get("row_label") or ""):
                    continue
                name = (entry.get("file") or "").split("/")[-1]
                sheet = entry.get("sheet") or ""
                key = (name, sheet)
                if key in seen:
                    continue
                seen.add(key)
                sheets.append(f"{name}" + (f" sheet {sheet}" if sheet else ""))
                if son is None and "(SON)" in name:
                    son = entry.get("file_id")
        sheets.sort(key=lambda label: (
            0 if "(SON)" in label else 1,
            0 if "VM" in label else 1,
            0 if "elektrik" not in label.lower() and "2-ci" not in label and "9336" not in label and "9337" not in label else 1,
            label,
        ))
    anchor = target["areas"][0]["value"] if target.get("areas") else None
    hatch = _garage_hatch(son, anchor) if son and anchor else None
    extra = []
    if sheets and finish is not None:
        named = "; ".join(sheets[:2])
        more = len(sheets) - 2
        if more > 0:
            named += f"; plus {more} other-order or background copies"
        extra.append(f"DWG room schedules print {finish:g} next to 1 Qaraj ({named})")
    if hatch is not None:
        extra.append(f"a floor hatch on (SON).dwg measures {hatch:.2f} m²")
    if not extra:
        return
    target["text"] += ". " + "; ".join(extra)
    side = f"{anchor:g}" if anchor is not None else "the floor schedule"
    target["text"] += f". The floor schedule, the PDF room schedule"
    if hatch is not None:
        target["text"] += f" and the hatch support {side}"
    else:
        target["text"] += f" support {side}"
    target["text"] += ". The finish schedule and the DWG text support the other area"


def _garage_hatch(file_id: str, anchor: float) -> float | None:
    import json
    from ..dwg.read import geom_path_for
    path = geom_path_for(file_id)
    if not path.exists() or not anchor:
        return None
    hatches = json.loads(path.read_text(encoding="utf-8")).get("hatches") or []
    closest = None
    for hatch in hatches:
        area = hatch.get("area_du2")
        if not area:
            continue
        metres = area / 1_000_000
        if abs(metres - anchor) / anchor > 0.01:
            continue
        if closest is None or abs(metres - anchor) < abs(closest - anchor):
            closest = metres
    return closest


def _attach_review_reasons(lines, out, take) -> None:
    from .provenance import review_reasons
    items = {item["id"]: item for item in take["items"]}
    links = {row["id"] for row in R.load("bill_map")}
    files = {row["sha256"]: row for row in (store.get("conversion") or {}).get("files") or []}
    for line in lines:
        row = out[line["id"]]
        row["review_reasons"] = review_reasons(row, items.get(row.get("item") or ""), links, files)


def _apply_decisions(out, take) -> None:
    """A person's link or choice. The chosen number has to be one already printed in the reason."""
    from ..reviews import active_reviews
    items = {item["id"]: item for item in take["items"]}
    for review in active_reviews():
        payload = review["payload"] if isinstance(review["payload"], dict) else {}
        row = out.get(review["target_id"])
        if review["action"] == "map" and review["target_kind"] == "line" and row is not None:
            item = items.get(payload.get("item") or "")
            if item is None:
                continue
            row.update({"status": "review", "item": item["id"], "our_qty": item["value"].get("value"),
                        "method": "manual", "reason": f"{review['author']} linked this line. {review['reason']}"})
        if review["action"] == "decide" and review["target_kind"] == "line" and row is not None:
            chosen = payload.get("value")
            if chosen is None:
                continue
            numbers = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", row.get("reason") or "")]
            if not any(abs(n - float(chosen)) <= 0.02 for n in numbers):
                continue
            row["our_qty"] = float(chosen)
            row["status"] = "review"
            row["method"] = "manual"
            row["reason"] = (row.get("reason") or "") + f" {review['author']} chose {float(chosen):g}. {review['reason']}"


def _mark_accepted(report: dict) -> None:
    from ..reviews import active_reviews
    accepted = {review["target_id"]: review["author"] for review in active_reviews()
                if review["action"] == "accept" and review["target_kind"] == "reason"}
    if not accepted:
        return
    for line_id, row in report["lines"].items():
        for reason in row.get("review_reasons") or []:
            author = accepted.get(f"reason:{line_id}:{reason.get('code')}")
            if author:
                reason["accepted_by"] = author


def _note_stated(lines, out, take, finder: Finder) -> None:
    """A quantity written in the description explains the line. It does not become the measured quantity."""
    for line in lines:
        stated = stated_quantity(line.get("description") or "")
        if not stated:
            continue
        bits = []
        if line.get("unit") == "m³" and stated["unit"] == "m²" and stated.get("thickness_m"):
            product = stated["qty"] * stated["thickness_m"]
            if close_at(line["qty"], product, bill_decimals(line["qty"])):
                bits.append(f"{line['qty']:g} = {stated['qty']:g} m² × {stated['thickness_m']:.2f} m, as the line itself says")
            else:
                bits.append(f"the line names {stated['qty']:g} m² × {stated['thickness_m']:.2f} m, and the billed quantity is {line['qty']:g}")
        found = _stated_on_drawing(line, stated, take["items"], finder)
        if found:
            bits.append(found)
        elif stated.get("thickness_m"):
            bits.append("that area is not a drawing measurement")
        if not bits:
            continue
        note = "; ".join(bits)
        row = out[line["id"]]
        row["stated"] = stated
        if row.get("status") == "not_found":
            row["reason"] = note
        else:
            reason = row.get("reason") or ""
            sentence = note[:1].upper() + note[1:]
            row["reason"] = f"{reason}. {sentence}" if reason else sentence


def _stated_on_drawing(line, stated, items, finder: Finder) -> str | None:
    hits = []
    for item in items:
        value = item["value"]
        if value.get("status") == "blocked" or value.get("value") is None:
            continue
        if item.get("unit") != stated["unit"] or item.get("building") != line.get("building"):
            continue
        if close_at(stated["qty"], value["value"], bill_decimals(stated["qty"])):
            hits.append(item)
    if len(hits) == 1:
        value = hits[0]["value"]["value"]
        return f"the line names {stated['qty']:g} {stated['unit']}; {hits[0]['label_en']} is {value:g} {stated['unit']}"
    if hits:
        return None
    strong, _weak = finder.direct(stated["qty"], stated["unit"], line.get("building"), line.get("description") or "")
    if len({round(e["value"], 4) for e in strong}) == 1:
        return f"the line names {stated['qty']:g} {stated['unit']}; it is printed on {strong[0]['file'].split('/')[-1]}"
    return None


def _ceramic_walls() -> list[dict]:
    """Ceramic wall areas on a finish schedule, tagged with the drawing's building."""
    import json
    from pathlib import Path

    from .. import config
    from ..schedules.finishes import finish_areas
    reg = {f["sha256"]: f for f in (store.get("register") or {"files": []})["files"]}
    found = []
    folder = config.CACHE_DIR / "pdf"
    if not folder.exists():
        return found
    for path in folder.glob("*.schedules.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        info = reg.get(data.get("sha256"), {})
        name = Path(data.get("file") or "").name
        for area in finish_areas(data.get("tables") or []):
            if area["side"] == "wall" and area["kind"] == "ceramic":
                found.append({**area, "file_id": data.get("sha256"), "file_name": name,
                              "building": info.get("building")})
    return found


def _tile_candidate(line: dict, areas: list[dict]) -> dict | None:
    """Tile facing stays a candidate until someone confirms it is the ceramic schedule."""
    rule = classify_rule(line.get("description"))
    if not rule or not rule.get("confirm") or line.get("unit") != "m²":
        return None
    cells = [a for a in areas if a.get("building") == line.get("building")]
    if not cells:
        return None
    total = sum(a["value"] for a in cells)
    parts = " + ".join(f"{a['value']:g}" for a in cells)
    return {
        "status": "review", "our_qty": None, "method": "schedule",
        "candidates": [_ceramic_source(a) for a in cells],
        "reason": f"ceramic wall areas {parts} = {total:g} m² are on the finish schedule; "
                  f"the bill says tile facing, and that mapping is not confirmed",
    }


def _ceramic_source(area: dict) -> dict:
    cell = area["cell"]
    return {"file_id": area.get("file_id"), "file_name": area.get("file_name"),
            "locator": {"kind": "pdf_span", "page": area.get("page"), "bbox": cell.get("bbox")},
            "raw_text": cell.get("text"), "decoded_text": area.get("description") or cell.get("text"),
            "row_label": area.get("floor")}


def source_decimals(v: dict) -> int | None:
    """Decimals as printed. Derived values have no printed precision."""
    if v.get("method") in ("derived", "geometry", "manual"):
        return None
    raw = next((s.get("decoded_text") for s in v.get("sources") or [] if s.get("decoded_text")), None)
    found = re.search(r"\d+(?:[.,](\d+))?", raw or "")
    return len(found.group(1) or "") if found else None


def auto_match_ok(item: dict, line: dict) -> bool:
    """An unlinked item matches a line only when they are the same element and the printed precision agrees."""
    if not item.get("billable", True):
        return False
    if not item.get("element") or item.get("element") != element_of_line(line.get("description") or ""):
        return False
    value = item["value"]
    d_bill = bill_decimals(line["qty"])
    d_src = source_decimals(value)
    decimals = d_bill if d_src is None else max(d_bill, d_src)
    return close_at(line["qty"], value["value"], decimals)


def _floors_by_group(lines) -> dict:
    out = {}
    for group in buildup_groups(lines):
        named = {classify(line.get("description")) for line in group["lines"]}
        named.discard(None)
        if len(named) != 1:
            continue
        floor = next(iter(named))
        for line in group["lines"]:
            out[line["id"]] = floor
    return out


def _on_this_floor(hits: list, floor: str | None) -> list:
    if not floor:
        return hits
    tagged = [e for e in hits if (e.get("row_label") or "").split(" ")[:1] == [floor]]
    return tagged or hits


def _schedule_notes() -> tuple[list[dict], list[dict]]:
    import json
    from .. import config
    from ..schedules.conflicts import cemi_conflicts
    tables, rooms = [], []
    folder = config.CACHE_DIR / "pdf"
    if folder.exists():
        for path in folder.glob("*.schedules.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            tables.extend(data.get("tables") or [])
            rooms.extend(data.get("rooms") or [])
    return same_room_conflicts(tables, rooms), cemi_conflicts(rooms)


def source_of_cell(area: dict) -> dict:
    cell = area["cell"]
    name = "9335 MH.pdf"
    sha = next((item.get("sha256") for item in (store.get("register") or {}).get("files") or []
                if (item.get("name") or "") == name or str(item.get("rel") or "").endswith(name)), None)
    return {"file_id": sha, "file_name": name, "locator": {"kind": "pdf_span", "page": area.get("page"),
            "bbox": cell.get("bbox")}, "raw_text": cell.get("text"), "decoded_text": cell.get("text")}


def _room_clash(line: dict, printed: float, conflicts: list[dict]) -> dict | None:
    key = fold_key(line.get("description") or "")
    if line.get("unit") != "m²" or not any(word in key for word in ("mozaik", "terraso")):
        return None
    for conflict in conflicts:
        if any(close_qty(printed, area["value"]) for area in conflict["areas"]):
            return conflict
    return None


def _propagate_groups(lines, out):
    """Lines that repeat the group's area take its drawing quantity. The 0.8 line does not."""
    for group in buildup_groups(lines):
        donors = []
        for line in group["lines"]:
            if line.get("unit") != "m²" or not close_qty(line["qty"], group["qty"]):
                continue
            row = out.get(line["id"]) or {}
            if row.get("status") in ("matched", "printed", "different") and row.get("our_qty") is not None:
                donors.append((line, row))
        values = {round(row["our_qty"], 4) for _, row in donors}
        if len(values) != 1:
            continue
        donor_line, donor = donors[0]
        for line in group["lines"]:
            if line.get("unit") != "m²" or not close_qty(line["qty"], group["qty"]):
                continue
            row = out.get(line["id"]) or {}
            if row.get("status") not in ("not_found", "review", "pending"):
                continue
            gap = line["qty"] - donor["our_qty"]
            copied = {k: donor.get(k) for k in ("our_qty", "method", "tolerance", "sources", "gap_pct")}
            out[line["id"]] = {**row, **copied, "status": donor["status"], "gap": None if donor["status"] != "different" else gap,
                               "group_from": donor_line["id"],
                               "reason": f"same build-up as {donor_line['id']}: {donor.get('reason')}"}


def _row_words(label: str | None) -> str:
    parts = (label or "").split()
    if not parts:
        return ""
    floor = _FLOOR_NAME.get(parts[0])
    if floor and len(parts) >= 2 and parts[1].isdigit():
        return f" ({floor}, type {parts[1]})"
    if floor:
        return f" ({floor})"
    return ""


def _sheet_counts(lines, out) -> None:
    """Plywood sheets: floor area ÷ sheet size printed in the bill line. The size is not on the drawing."""
    for group in buildup_groups(lines):
        _parent, parent_row = _group_parent(group, out)
        area = parent_row.get("our_qty")
        if area is None:
            continue
        for line in group["lines"]:
            if line.get("unit") != "each":
                continue
            found = re.search(r"(\d+[.,]\d+)\s*[*x×]\s*(\d+[.,]\d+)", line.get("description") or "")
            if not found:
                continue
            width = float(found.group(1).replace(",", "."))
            height = float(found.group(2).replace(",", "."))
            if width <= 0 or height <= 0:
                continue
            raw = area / (width * height)
            sheets = int(raw + 0.999)
            row = out.get(line["id"]) or {}
            if row.get("status") not in ("not_found", "review", "pending"):
                continue
            if not close_at(line["qty"], sheets, bill_decimals(line["qty"])):
                continue
            out[line["id"]] = {
                **row, "status": "review", "our_qty": float(sheets), "factor_source": "bill_text",
                "reason": f"{area:g} m² ÷ ({width:g} × {height:g} m) = {raw:.1f}, rounded up to {sheets:g} sheets. "
                          f"The sheet size is in the bill line, not on the drawing.",
            }


def _coverage_hints(lines, out) -> None:
    """104 = 130 × 0.8 is the estimator's joist coverage. It is a hint, not a measurement."""
    hits = []
    for group in buildup_groups(lines):
        if not group["qty"]:
            continue
        for line in group["lines"]:
            if line.get("unit") != "m²" or not line.get("qty"):
                continue
            if close_qty(line["qty"], group["qty"]):
                continue
            if abs(line["qty"] / group["qty"] - 0.8) > 0.001:
                continue
            hits.append((line, group))
    if len(hits) < 2:
        return
    for line, group in hits:
        row = out.get(line["id"]) or {}
        if row.get("status") not in ("not_found", "review", "pending"):
            continue
        parent, parent_row = _group_parent(group, out)
        others = [other["id"] for other, _ in hits if other["id"] != line["id"]]
        shown = parent_row.get("our_qty") if parent_row else None
        if shown is None and parent is not None:
            shown = parent["qty"]
        hint = round(parent_row["our_qty"] * 0.8, 4) if parent_row and parent_row.get("our_qty") is not None else None
        name = parent["id"] if parent else "the floor"
        other = others[0]
        amount = f"{shown:g} m²" if shown is not None else "the floor area"
        out[line["id"]] = {
            **row, "status": "review", "our_qty": hint, "coverage": 0.8,
            "reason": f"0.8 × {name} ({amount})"
                      + (f" = {hint:g} m²" if hint is not None else "")
                      + f", the same ratio as {other}. This is the estimator's coverage, not a measurement on the drawing.",
        }


def _volume_hints(lines, out, rows=None) -> None:
    """A polystyrene volume on the 0.8 area uses a thickness the floor schedule prints. The 0.8 does not."""
    if rows is None:
        rows = _floor_rows()
    if not rows:
        return
    for group in buildup_groups(lines):
        coverage = _coverage_line(group)
        if coverage is None:
            continue
        for line in group["lines"]:
            row = out.get(line["id"]) or {}
            if line.get("unit") != "m³" or row.get("status") not in ("not_found", "review", "pending"):
                continue
            fit = _printed_thickness(line, group, coverage["qty"], rows)
            if fit is None:
                continue
            sched, thickness = fit
            area = _coverage_area(group, coverage, out)
            hint = round(area * thickness / 1000, 4) if area is not None else None
            floor = _FLOOR_NAME.get(sched["floor"], sched["floor"])
            amount = f"{area:g} m²" if area is not None else "the coverage area"
            out[line["id"]] = {
                **row, "status": "review", "our_qty": hint,
                "reason": f"{coverage['id']} is {amount} × {thickness:g} mm"
                          + (f" = {hint:g} m³" if hint is not None else "")
                          + f". The {thickness:g} mm is printed on the {floor} type {sched['type_no']}. "
                          f"The 0.8 coverage is not on the drawing, so this volume is not a measurement.",
            }


def _coverage_line(group):
    if not group["qty"]:
        return None
    for line in group["lines"]:
        if line.get("unit") == "m²" and line.get("qty") and abs(line["qty"] / group["qty"] - 0.8) <= 0.001:
            return line
    return None


def _coverage_area(group, coverage, out):
    row = out.get(coverage["id"]) or {}
    if row.get("our_qty") is not None:
        return row["our_qty"]
    _parent, parent_row = _group_parent(group, out)
    if parent_row.get("our_qty") is not None:
        return round(parent_row["our_qty"] * 0.8, 4)
    return None


def _printed_thickness(line, group, coverage_qty, rows):
    fits = []
    for sched in rows:
        if sched.get("building") != line.get("building"):
            continue
        if not close_qty(sched["area"], group["qty"]):
            continue
        for layer in sched["layers"]:
            thickness = layer.get("thickness_mm")
            if not thickness or not _shares_layer(line.get("description") or "", layer.get("text") or ""):
                continue
            if close_at(line["qty"], coverage_qty * thickness / 1000, bill_decimals(line["qty"])):
                fits.append((sched, thickness))
    if len(fits) != 1:
        return None
    return fits[0]


def _shares_layer(description: str, layer_text: str) -> bool:
    bill, layer = fold_key(description), fold_key(layer_text)
    return any(stem in bill and stem in layer for stem in ("penopolist", "keramzit", "qum"))


def _floor_rows() -> list[dict]:
    import json
    from pathlib import Path

    from .. import config
    from ..schedules.layers import floor_rows
    reg = {f["sha256"]: f for f in (store.get("register") or {"files": []})["files"]}
    found = []
    folder = config.CACHE_DIR / "pdf"
    if not folder.exists():
        return found
    for path in folder.glob("*.schedules.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        info = reg.get(data.get("sha256"), {})
        for row in floor_rows(data.get("tables") or []):
            found.append({**row, "building": info.get("building"), "file_name": Path(data.get("file") or "").name})
    return found


_FLOOR_NAME = {"basement": "basement", "floor_1": "1st floor", "floor_2": "2nd floor", "roof": "roof"}


def _group_parent(group, out):
    chosen = None
    for line in group["lines"]:
        if line.get("unit") != "m²" or not close_qty(line["qty"], group["qty"]):
            continue
        row = out.get(line["id"]) or {}
        if row.get("our_qty") is not None:
            return line, row
        if chosen is None:
            chosen = (line, row)
    return chosen if chosen else (None, {})


def _subject_swap(line: dict, strong: list, finder: Finder) -> dict | None:
    """A printed L= whose sentence names the other element is not this line's quantity."""
    kind = subject_class(line["description"])
    if not kind:
        return None
    names = {"gutter": "gutters (nov)", "downpipe": "downpipes (novalça)"}
    labeled = [(e, subject_class(e.get("context") or "")) for e in strong]
    labeled = [(e, c) for e, c in labeled if c]
    if any(c == kind for _, c in labeled) or not labeled:
        return None
    wrong, wrong_kind = labeled[0]
    right = finder.for_subject(line["building"], line["unit"], kind)
    values = {round(e["value"], 4) for e in right}
    if len(values) != 1:
        return {"status": "review", "our_qty": None, "sources": [source_of(wrong)],
                "reason": f"the drawing gives {wrong['value']:g} {line['unit']} to {names.get(wrong_kind, wrong_kind)}; "
                          f"the bill gives it to {names.get(kind, kind)}"}
    drawing = right[0]["value"]
    if close_at(line["qty"], drawing, bill_decimals(line["qty"])):
        return None
    gap = round(line["qty"] - drawing, 4)
    return {"status": "different", "our_qty": drawing, "method": "stated", "gap": gap,
            "gap_pct": gap / drawing * 100 if drawing else None,
            "gap_money": None if line.get("rate") is None else gap * line["rate"],
            "tolerance": f"exact at {bill_decimals(line['qty'])} decimals",
            "reason": f"the drawing gives {wrong['value']:g} {line['unit']} to {names.get(wrong_kind, wrong_kind)}; "
                      f"the bill gives it to {names.get(kind, kind)}. {names.get(kind, kind)} are {drawing:g} {line['unit']}",
            "sources": [source_of(right[0]), source_of(wrong)]}


def _derived(lines, out):
    """Repeats and tonnes from m³ inherit a checked line in the same build-up, in either direction."""
    by_section = defaultdict(list)
    for l in lines:
        by_section[l["section"]].append(l)
    member = {}
    for group in buildup_groups(lines):
        ids = [line["id"] for line in group["lines"]]
        for line in group["lines"]:
            member[line["id"]] = ids
    for sec_lines in by_section.values():
        order = {line["id"]: i for i, line in enumerate(sec_lines)}
        for l in sec_lines:
            r = out.get(l["id"], {})
            if r.get("status") not in (None, "pending", "not_found", "review"):
                continue
            if l["id"] in member:
                pool = [line for line in sec_lines if line["id"] in member[l["id"]] and line["id"] != l["id"]]
            else:
                pool = [line for line in sec_lines if line["id"] not in member and line["id"] != l["id"]]
            pool.sort(key=lambda line: abs(order[line["id"]] - order[l["id"]]))
            for parent in pool:
                pr = out.get(parent["id"], {})
                if pr.get("status") not in CHECKED:
                    continue
                parent_ours = pr.get("our_qty")
                if parent_ours is None:
                    continue
                if parent["unit"] == l["unit"] and close_at(parent["qty"], l["qty"], bill_decimals(l["qty"])):
                    repeat = REPEAT_WORDS.search(l["description"] or "")
                    if l["unit"] == "each" and not repeat:
                        continue
                    kind = "repeat" if repeat else "same quantity"
                    out[l["id"]] = {"status": "derived", "derived_from": parent["id"], "our_qty": parent_ours,
                                    "kind": kind, "method": "derived",
                                    "tolerance": f"exact at {bill_decimals(l['qty'])} decimals",
                                    "reason": f"{'repeats' if kind == 'repeat' else 'same quantity as'} line {parent['id']} "
                                              f"({parent_ours:g} {parent['unit']})"}
                    break
                if l["unit"] == "t" and parent["unit"] == "m³" and parent["qty"]:
                    ratio = round(l["qty"] / parent["qty"], 3)
                    if any(abs(ratio - d) < 1e-6 for d in DENSITIES):
                        ours = _round_bill(parent_ours * ratio, l["qty"])
                        out[l["id"]] = {"status": "derived", "derived_from": parent["id"], "our_qty": ours,
                                        "kind": "density", "density": ratio, "method": "derived",
                                        "tolerance": f"exact at {bill_decimals(l['qty'])} decimals",
                                        "reason": f"{parent_ours:g} m³ × {ratio:g} t/m³ from line {parent['id']}; the "
                                                  f"density is the estimator's choice, not on a drawing"}
                        break


def _summarise(bill, take, out, linked_items) -> dict:
    lines = bill["lines"]
    counts = Counter(r["status"] for r in out.values())
    value = defaultdict(float)
    for l in lines:
        value[out[l["id"]]["status"]] += l["amount"] or 0.0  # allow-default: money total, not a quantity
    by_building = defaultdict(lambda: {"value": 0.0, "checked": 0.0, "lines": 0, "checked_lines": 0})
    for l in lines:
        b = by_building[l["building"]]
        b["value"] += l["amount"] or 0.0  # allow-default: money total, not a quantity
        b["lines"] += 1
        if out[l["id"]]["status"] in CHECKED | {"different"}:
            b["checked"] += l["amount"] or 0.0  # allow-default: money total, not a quantity
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
    for row in sorted(lists["different"], key=lambda r: -abs((r["gap"] or 0) * ((r["amount"] or 0) / (r["bill_qty"] or 1)))):  # allow-default: money sort, not a quantity
        attention.append({"kind": "different", "id": row["id"], "label": row["description"][:90], "label_az": row["description"],
                          "detail": row["reason"]})
    runlog.event("match", "info", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return {"lines": out, "counts": dict(counts), "value_by_status": {k: round(v, 2) for k, v in value.items()},
            "lists": lists, "value_by_building": value_by_building, "measured_no_bill_line": items_unlinked,
            "attention": attention[:30], "total_value": round(sum(l["amount"] or 0 for l in lines), 2)}  # allow-default: money total, not a quantity
