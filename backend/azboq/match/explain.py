"""Flatten one bill line so the drawer can show the formula and every source."""
from __future__ import annotations


def substitute(value: dict) -> str | None:
    """The formula with each input's number in place, then the result."""
    formula = value.get("formula")
    if not formula or value.get("value") is None:
        return None
    text = formula
    for name, child in sorted((value.get("inputs") or {}).items(), key=lambda kv: -len(kv[0])):
        if child.get("value") is None:
            continue
        text = text.replace(name, f"{child['value']:g}")
    return f"{text} = {value['value']:g} {value.get('unit') or ''}".strip()


def explain_line(line_id: str, bill: dict, report: dict, takeoff: dict) -> dict | None:
    line = next((item for item in bill["lines"] if item["id"] == line_id), None)
    if line is None:
        return None
    result = report["lines"].get(line_id) or {}
    item = next((row for row in takeoff["items"] if row["id"] == result.get("item")), None)
    value = item["value"] if item else None

    def leaves(node: dict, path: list[str]):
        inputs = node.get("inputs") or {}
        if not inputs:
            yield {
                "path": path,
                "name": path[-1] if path else "",
                "value": node.get("value"),
                "unit": node.get("unit"),
                "method": node.get("method"),
                "status": node.get("status"),
                "label": _label(path[-1] if path else "", node),
                "sources": [_source_view(s) for s in node.get("sources") or []],
            }
            return
        for name, child in inputs.items():
            yield from leaves(child, path + [name])

    chain = []
    current = result
    seen = set()
    while current.get("derived_from") and len(chain) < 8:
        parent_id = current["derived_from"]
        if parent_id in seen:
            break
        seen.add(parent_id)
        chain.append({
            "line": parent_id,
            "relation": current.get("kind"),
            "factor": current.get("density") or current.get("coverage"),
        })
        current = report["lines"].get(parent_id) or {}

    return {
        "line": {key: line[key] for key in ("id", "description", "unit", "qty", "rate", "amount", "row")},
        "result": {key: result.get(key) for key in (
            "status", "our_qty", "gap", "gap_pct", "tolerance", "reason", "floor", "factor_source")},
        "item": None if not item or not value else {
            "id": item["id"],
            "label_en": item.get("label_en"),
            "label_az": item.get("label_az"),
            "citation": item.get("citation"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "method": value.get("method"),
            "formula": value.get("formula"),
            "substituted": substitute(value),
        },
        "inputs": list(leaves(value, [])) if value else [],
        "printed": [_source_view(s) for s in result.get("sources") or []],
        "chain": chain,
        "review_reasons": result.get("review_reasons") or [],
        "searched": (value or {}).get("searched") or [],
        "rejected": (value or {}).get("rejected") or [],
    }


def _label(name: str, node: dict) -> str:
    source = (node.get("sources") or [{}])[0]
    loc = source.get("locator") or {}
    if loc.get("row") and loc.get("col"):
        return f"{loc['row']} · {loc['col']}"
    note = node.get("note") or ""
    if note and note != name:
        return note.split("|")[0].strip()
    return name


def _source_view(source: dict) -> dict:
    loc = source.get("locator") or {}
    return {
        "file": source.get("file_name"),
        "file_id": source.get("file_id"),
        "sheet": loc.get("sheet"),
        "page": loc.get("page"),
        "region": loc.get("region"),
        "handle": loc.get("handle"),
        "table": loc.get("table"),
        "row": loc.get("row"),
        "col": loc.get("col"),
        "printed": source.get("decoded_text"),
        "raw": source.get("raw_text"),
        "bbox": loc.get("span_bbox") or loc.get("bbox"),
        "at": loc.get("at"),
        "is_rule": source.get("file_id") == "rule",
        "rule_id": loc.get("rule_id"),
        "citation": loc.get("citation"),
    }
