"""Every printed number in the package, with its unit, context and exact place.

The index feeds the evidence finder (match/evidence.py) and the resolvers in the
takeoff engine. Small round integers are kept but marked weak; they match too
much to be evidence on their own.
"""
import re

from ..text.normalise import numbers_in

UNIT_AFTER = re.compile(r"^\s*(m³|m3|m²|m2|m\b|p\.?m\.?|pm\b|kq|kg|ton|t\b|əd\.?|ədəd|dəst|sm|mm|km|l/s|kVt|kVA)",
                        re.I)
UNIT_CANON = {"m3": "m³", "m³": "m³", "m2": "m²", "m²": "m²", "m": "m", "pm": "m", "p.m": "m", "p.m.": "m", "kq": "kg",
              "kg": "kg", "ton": "t", "t": "t", "əd": "each", "əd.": "each", "ədəd": "each", "dəst": "set", "sm": "cm",
              "mm": "mm", "km": "km"}


def _unit_after(text: str, end: int) -> str | None:
    m = UNIT_AFTER.match(text[end:end + 8])
    if not m:
        return None
    return UNIT_CANON.get(m.group(1).lower().rstrip("."), m.group(1))


def strength(value: float, token: str) -> str:
    digits = len(re.sub(r"\D", "", token))
    has_decimal = bool(re.search(r"[.,]\d", token))
    if has_decimal and digits >= 3:
        return "strong"
    if not has_decimal and digits >= 4:
        return "strong"
    return "weak"


NUMBER_TOKEN = re.compile(r"(?<![\w.,\-/])[-+±]?\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d+)?(?![\w])|"
                          r"(?<![\w.,\-/])[-+±]?\d+(?:[.,]\d+)?(?![\w.,]\d)")


def entries_from_text(text: str, base: dict) -> list[dict]:
    """Numbers standing on their own; digits inside codes (A240, Mk-1, ME-2100, Ø8) are not quantities."""
    out = []
    for m in NUMBER_TOKEN.finditer(text):
        tok = m.group(0)
        vals = numbers_in(tok)
        if not vals:
            continue
        value = abs(vals[0][1])
        if value == 0:
            continue
        out.append({**base, "value": round(value, 4), "token": tok, "unit": _unit_after(text, m.end()),
                    "strength": strength(value, tok), "context": text[:200]})
    return out


def _row_labels(texts: list[dict], reach: float = 80.0) -> list[str]:
    """For each text, the texts on the same row to its left (the row label of a table cell)."""
    order = sorted(range(len(texts)), key=lambda i: texts[i]["at"][1])
    ys = [texts[i]["at"][1] for i in order]
    labels = [""] * len(texts)
    import bisect
    for pos, i in enumerate(order):
        t = texts[i]
        h = max(t.get("h") or 0.0, 1e-6)
        lo = bisect.bisect_left(ys, t["at"][1] - h * 0.6)
        hi = bisect.bisect_right(ys, t["at"][1] + h * 0.6)
        left = [texts[order[k]] for k in range(lo, hi) if order[k] != i and
                0 < t["at"][0] - texts[order[k]]["at"][0] <= h * reach]
        left.sort(key=lambda o: o["at"][0])
        labels[i] = " ".join(o["text"].replace("\n", " ") for o in left)[-160:]
    return labels


def build_index(drawings: list[dict], pdfs: list[dict], regions_by_file: dict, file_info: dict) -> list[dict]:
    from ..sheets import region_of
    idx = []
    for d in drawings:
        regions = regions_by_file.get(d["sha256"], [])
        fb = file_info.get(d["sha256"], {})
        rmap = {r["id"]: r for r in regions}
        rmap[None] = {"building": fb.get("building"), "discipline": fb.get("discipline"), "number": None}
        labels = _row_labels(d["texts"])
        for t, label in zip(d["texts"], labels):
            rid = region_of(t["at"], regions)
            r = rmap.get(rid, {})
            base = {"file_id": d["sha256"], "file": d["file"], "kind": "dxf_text", "handle": t["handle"],
                    "layer": t["layer"], "role": t["role"], "region": rid, "at": t["at"],
                    "building": r.get("building"), "discipline": r.get("discipline"),
                    "sheet": (r.get("number") or {}).get("raw"), "row_label": label}
            idx.extend(entries_from_text(t["text"], base))
        for dim in d["dims"]:
            rid = region_of(dim["at"], regions)
            r = rmap.get(rid, {})
            shown = dim["text"] if dim["text"] and dim["text"] != "<>" else None
            if dim["measurement"] is None:
                continue
            base = {"file_id": d["sha256"], "file": d["file"], "kind": "dxf_dim", "handle": dim["handle"],
                    "layer": dim["layer"], "role": dim["role"], "region": rid, "at": dim["at"],
                    "building": r.get("building"), "discipline": r.get("discipline"),
                    "sheet": (r.get("number") or {}).get("raw"), "measurement": dim["measurement"],
                    "override": shown}
            value = round(dim["measurement"], 3)
            idx.append({**base, "value": value, "token": shown or f"{value:g}", "unit": "mm?",
                        "strength": strength(value, f"{value:g}"), "context": f"dimension {value:g}"})
    for p in pdfs:
        for page in p["pages"]:
            lines = page["lines"]
            for line in lines:
                x0, y0, x1, y1 = line["bbox"]
                h = max(y1 - y0, 1e-6)
                left = sorted((l for l in lines if l is not line and abs((l["bbox"][1] + l["bbox"][3]) / 2 - (y0 + y1) / 2) <= h * 0.6
                               and l["bbox"][2] <= x0 + 1), key=lambda l: l["bbox"][0])
                base = {"file_id": p["sha256"], "file": p["file"], "kind": "pdf_line", "page": page["page"],
                        "bbox": line["bbox"], "building": page.get("building"), "discipline": page.get("discipline"),
                        "sheet": (page.get("number") or {}).get("raw"),
                        "row_label": " ".join(l["text"] for l in left)[-160:]}
                idx.extend(entries_from_text(line["text"], base))
    return idx
