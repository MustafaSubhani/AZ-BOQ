"""Why a value needs a person to look at it. Never labelled as a measured drawing fact."""


def review_reasons(line_result: dict, item: dict | None, bill_map_ids: set[str], files: dict | None = None) -> list[dict]:
    found = []
    files = files or {}
    sources = []

    def walk(value: dict):
        if value.get("method") == "rule":
            loc = ((value.get("sources") or [{}])[0]).get("locator") or {}
            found.append({"code": "project_rule", "rule": loc.get("rule_id"), "citation": loc.get("citation")})
        if value.get("method") == "manual":
            found.append({"code": "manual", "note": value.get("note")})
        if value.get("conflicts"):
            found.append({"code": "conflict", "n": len(value["conflicts"])})
        for source in value.get("sources") or []:
            sources.append(source)
            file_row = files.get(source.get("file_id"))
            if file_row and file_row.get("status") == "single reader":
                found.append({"code": "single_reader", "file": file_row.get("name") or file_row.get("file")})
        for child in (value.get("inputs") or {}).values():
            walk(child)

    if item:
        walk(item["value"])
    if line_result.get("method") == "manual":
        found.append({"code": "manual", "note": line_result.get("reason")})
    if line_result.get("link") in bill_map_ids:
        found.append({"code": "hand_link", "link": line_result["link"]})
    if line_result.get("kind") == "density" or line_result.get("coverage"):
        found.append({"code": "estimator_factor"})
    if line_result.get("factor_source") == "bill_text":
        found.append({"code": "bill_text_factor"})
    if line_result.get("status") == "review" and "658.30" in (line_result.get("reason") or ""):
        found.append({"code": "conflict"})
    if sources and all((source.get("locator") or {}).get("only_other_order") for source in sources):
        sheet = (sources[0].get("locator") or {}).get("sheet") or sources[0].get("file_name")
        found.append({"code": "copy_only", "file": sheet})
    seen = set()
    unique = []
    for reason in found:
        key = (reason["code"], reason.get("rule") or reason.get("link") or reason.get("file"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(reason)
    return unique
