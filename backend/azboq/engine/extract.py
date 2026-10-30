"""Rule types. Each reads by context (row labels, note expressions, plan dimensions, level marks) and
returns a Value with its sources, or BLOCKED with the places it looked."""
import re
from collections import Counter

from .. import store
from ..text.normalise import fold_key, numbers_in
from ..values import Method, Status, Value, blocked, derive
from . import locate as L

LEVEL = re.compile(r"^[±+\-]?\s?\d{1,2}[.,]\d{3}$")
# Reading parameters a rule may override. They shape where to look, never a quantity.
READ_DEFAULTS = {"pick": 0, "row_tol": 0.6, "row_reach": 60}


def _params(rule) -> dict:
    return {**READ_DEFAULTS, **rule}


def _reach(t, factor) -> float | None:
    """Row reach in drawing units; a text with no height gets no reach (exact column only)."""
    return t["h"] * factor if t.get("h") else None


def _conversion_files() -> dict:
    conv = store.get("conversion") or {"files": []}
    return {f["sha256"]: f for f in conv["files"]}


def lineage(src) -> tuple:
    """Sources confirm each other only when this key differs. A plot of a sheet shares the sheet's key."""
    from ..dwg.layers import role as layer_role
    loc = src.locator or {}
    if loc.get("kind") == "rule":
        return ("rule", loc.get("rule_id"))
    info = L.files().get(src.file_id, {})
    num = {}
    if str(loc.get("kind") or "").startswith("pdf") and loc.get("page") is not None:
        pages = (L.pdf(src.file_id) or {}).get("pages") or []
        page = pages[loc["page"]] if 0 <= loc["page"] < len(pages) else {}
        num = page.get("number") or {}
    elif loc.get("region"):
        region = next((r for r in L.regions(src.file_id) if r["id"] == loc["region"]), None)
        num = (region or {}).get("number") or {}
    sheet = (num.get("mark"), num.get("discipline_mark")) if num.get("mark") else (info.get("building"), info.get("discipline"))
    if loc.get("layer") and layer_role(loc["layer"]) == "architecture_background":
        sheet = ("architecture", info.get("building"))
    return ("sheet", sheet, loc.get("table"))


def _independent(sources) -> bool:
    return len({lineage(s) for s in sources}) >= 2


def _source_affected(src, cross: dict) -> bool:
    """A reader disagreement matters only for the entity type or the layer this source came from."""
    kind = {"dxf_entity": ("TEXT", "MTEXT", "ATTRIB", "MULTILEADER"),
            "dxf_dimension": ("DIMENSION",)}.get(src.locator.get("kind"), ())
    types = {d.get("type") for d in cross.get("type_diffs") or []}
    layers = {d.get("layer") for d in cross.get("layer_diffs") or []}
    return bool(set(kind) & types) or src.locator.get("layer") in layers


def _files_for(rule) -> list[str]:
    out = []
    for name in rule.get("files", []):
        out.extend(L.dwg_files(name))
    return list(dict.fromkeys(out))


def _pdfs_for(rule) -> list[str]:
    out = []
    for name in rule.get("pdfs", []):
        out.extend(L.pdf_files(name))
    return list(dict.fromkeys(out))


def _searched(rule) -> list[str]:
    """The files the rule names, plus the sheet titles on those files for this building."""
    shas = _files_for(rule) + _named_pdfs(rule)
    where = f" (sheets classified {rule['building']})" if rule.get("building") else ""
    names = []
    stored = L.sheets() or {}
    for sha in shas:
        rel = L.files()[sha]["rel"]
        names.append(f"{rel}{where}")
        info = (stored.get("dwg") or {}).get(sha) or (stored.get("pdf") or {}).get(sha) or {}
        titles = []
        for region in info.get("regions") or []:
            if rule.get("building") and region.get("building") != rule["building"]:
                continue
            if region.get("title"):
                titles.append(region["title"])
        for page in info.get("pages") or []:
            if rule.get("building") and page.get("building") != rule["building"]:
                continue
            if page.get("title"):
                titles.append(page["title"])
        for title in sorted(set(titles))[:8]:
            names.append(f"{rel} · {title}")
    return names or ["no file matched the rule's file list"]


def _status(sources, verified: bool) -> tuple[Status, str]:
    conv = _conversion_files()
    affected = []
    for s in sources:
        row = conv.get(s.file_id)
        if not row or row.get("status") != "reader disagreement":
            continue
        if _source_affected(s, row.get("crosscheck") or {}):
            affected.append(s.file_name)
    if affected:
        return Status.REVIEW, f"ODA and LibreDWG disagree on {', '.join(sorted(set(affected)))}"
    other_order = [(s.locator or {}).get("only_other_order") for s in sources]
    if sources and all(other_order):
        return Status.REVIEW, "the only copy of this sheet carries another order number"
    kinds = {(s.locator or {}).get("kind") for s in sources}
    plot = any(str(k).startswith("dxf") for k in kinds) and any(str(k).startswith("pdf") for k in kinds) and not verified
    note = "read twice (DWG and its plot); that confirms the reading, not a second measurement" if plot else ""
    return (Status.VERIFIED if verified else Status.EXTRACTED), note


def _value(rule, value, sources, method, verified=False, note="", conflicts=(), rejected=()):
    del verified  # a second copy or the PDF plot of the same sheet is not a second fact
    status, extra = _status(sources, _independent(sources))
    if conflicts:
        status = Status.REVIEW
    return Value(round(float(value), 4), rule["unit"], method, status, sources=tuple(sources[:12]),
                 searched=tuple(_searched(rule)), conflicts=tuple(conflicts), rejected=tuple(rejected),
                 note="; ".join(x for x in (note, extra) if x))


def _named_pdfs(rule) -> list[str]:
    """Only PDFs the rule names. There is no silent search of the depot set."""
    names = list(rule.get("pdfs") or [])
    cross = (rule.get("cross_check_text") or {}).get("pdf")
    if cross:
        names.append(cross)
    out = []
    for name in names:
        out.extend(L.pdf_files(name))
    return list(dict.fromkeys(out))


def _pdf_confirms(rule, value: float, text_of=None, page_ok=None) -> list:
    """A PDF line that prints the same number, on a page of this building."""
    out = []
    building = rule.get("building")
    for sha in _named_pdfs(rule):
        file_building = L.files()[sha].get("building")
        for page in L.pdf(sha)["pages"]:
            if page.get("copy_of"):
                continue
            if building and (page.get("building") or file_building) != building:
                continue
            if page_ok and not page_ok(page):
                continue
            for line in page["lines"]:
                for _, v in numbers_in(line["text"]):
                    if abs(v - value) < 1e-6 and (text_of is None or text_of(line["text"])):
                        out.append(L.pdf_source(sha, page["page"], line))
                        break
    return out


def _is_section_page(src) -> bool:
    if src.locator.get("kind") != "pdf_span":
        return False
    page = L.pdf(src.file_id)["pages"][src.locator["page"]]
    return bool(re.search(r"kesim", fold_key(" ".join(l["text"] for l in page["lines"]))))


def _depot_dims(rule):
    for sha in _files_for(rule):
        for dim in L.dump(sha)["dims"]:
            if dim["measurement"] is None:
                continue
            region = L.region_of(sha, dim["at"])
            building = region["building"] if region else L.files()[sha].get("building")
            if building != rule["building"]:
                continue
            if region and region.get("copy_of"):
                continue
            yield sha, dim, region


def _is_plan(region) -> bool:
    """A floor or roof plan. A facade, a section, and the site 'Baş plan' are not."""
    if not region:
        return False
    key = fold_key(region.get("title") or "")
    if "fasad" in key or "kesim" in key or "bas plan" in key:
        return False
    return "plani" in key or re.search(r"(^|[^a-z])plan([^a-z]|$)", key) is not None


def dimension_extreme(rule, horizontal: bool) -> Value:
    lo, hi = rule["range"]
    found = []
    for sha, dim, region in _depot_dims(rule):
        if not _is_plan(region):
            continue
        m = dim["measurement"]
        if not (lo <= m <= hi) or not dim.get("p1") or not dim.get("p2"):
            continue
        dx = abs(dim["p2"][0] - dim["p1"][0])
        dy = abs(dim["p2"][1] - dim["p1"][1])
        if (dx >= dy) != horizontal:
            continue
        found.append((round(m, 1), sha, dim, region))
    if not found:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "no overall plan dimension found", Method.GEOMETRY)
    counts = Counter(m for m, *_ in found)
    repeated = [m for m, n in counts.items() if n >= 2] or list(counts)
    best = max(repeated)
    srcs = [L.dim_source(sha, dim, region) for m, sha, dim, region in found if m == best]
    confirm = _pdf_confirms(rule, round(best), page_ok=_is_plan)
    return _value(rule, best * rule["factor"], srcs + confirm, Method.GEOMETRY, verified=bool(confirm),
                  note=f"largest repeated {'horizontal' if horizontal else 'vertical'} plan dimension, "
                       f"{counts[best]} dimensions measure {best:g}")


def dimension_mode(rule) -> Value:
    lo, hi = rule["range"]
    found = [(round(d["measurement"]), sha, d, r) for sha, d, r in _depot_dims(rule) if lo <= d["measurement"] <= hi]
    if not found:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "", Method.GEOMETRY)
    counts = Counter(m for m, *_ in found)
    best, n = counts.most_common(1)[0]
    srcs = [L.dim_source(sha, d, r) for m, sha, d, r in found if m == best][:8]
    return _value(rule, best * rule["factor"], srcs, Method.GEOMETRY,
                  note=f"most common plan dimension between {lo} and {hi}: {best} ({n} dimensions)")


def slab_level_step(rule) -> Value:
    pat = re.compile(rule["title_pattern"])
    levels: dict[float, list] = {}
    for sha in _files_for(rule):
        for t, region in L.texts_in(sha, rule["building"]):
            m = pat.search(fold_key(t["text"]))
            if m:
                v = float(m.group(1).replace(",", "."))
                levels.setdefault(v, []).append(L.dxf_source(sha, t, region))
    if len(levels) < 2:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "fewer than two slab levels named in sheet titles",
                       Method.STATED)
    lv = sorted(levels)
    steps = Counter(round(b - a, 3) for a, b in zip(lv, lv[1:]))
    step, n = steps.most_common(1)[0]
    srcs = [levels[v][0] for v in lv]
    rejected = [{"step": s, "count": c} for s, c in steps.items() if s != step]
    return _value(rule, step, srcs, Method.STATED,
                  note=f"slab levels {', '.join(f'{v:+.2f}' for v in lv)}; step {step:.2f} m occurs {n}×",
                  rejected=rejected)


def floor_level_depth(rule) -> Value:
    counts: Counter = Counter()
    srcs: dict[float, list] = {}
    for sha in _files_for(rule):
        for t, region in L.texts_in(sha, rule["building"], rule.get("region_title")):
            s = t["text"].strip()
            if LEVEL.match(s):
                v = float(s.replace("±", "").replace(" ", "").replace(",", "."))
                counts[v] += 1
                srcs.setdefault(v, []).append(L.dxf_source(sha, t, region))
    deep = sorted(((n, v) for v, n in counts.items() if v <= -2.0), reverse=True)
    if not deep:
        return blocked(rule["unit"], [rule["id"]], _searched(rule),
                       "no basement floor mark on a sheet titled as the basement plan", Method.STATED)
    ground_src = srcs.get(0.0, [])[:1]
    # A section drawing that prints the same height as a dimension confirms one candidate.
    confirmed = []
    for c, v in deep:
        mm = round(-v * 1000)
        conf = [s for s in _pdf_confirms(rule, mm) if True]
        section = [s for s in conf if _is_section_page(s)]
        if section:
            confirmed.append((v, c, section))
    if confirmed:
        floor, n, section = confirmed[0]
        rejected = [{"level": v, "count": c, "why": "no section dimension confirms it"} for c, v in deep if v != floor]
        return _value(rule, 0.0 - floor, srcs[floor][:3] + ground_src + section[:2], Method.STATED, verified=True,
                      note=f"basement floor mark {floor:+.3f} ({n}× on the basement plan) confirmed by the section "
                           f"dimension {round(-floor * 1000)}", rejected=rejected)
    n, floor = deep[0]
    others = [{"value": round(-v, 3), "count": c, "why": "another floor mark on the basement plan"} for c, v in deep[1:]]
    return _value(rule, 0.0 - floor, srcs[floor][:4] + ground_src, Method.STATED,
                  note=f"most common floor mark on the basement plan: {floor:+.3f} ({n}×); no section confirms it",
                  conflicts=others[:4])


_STANDALONE_NUM = re.compile(r"(?<![\w\-])[-+]?\d+(?:[.,]\d+)?\s*(m³|m²|m3|m2|m\b|əd\.?|ədəd)?")
_CELL_NUM = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(m³|m²|m3|m2|m|əd\.?|ədəd|kq|kg|t)?\s*$")


NOTE_WORDS = 12  # a schedule label is a few words; a longer text is a note sentence that happens to share them


def _anchor_match(pattern, text) -> bool:
    stripped = _STANDALONE_NUM.sub(" ", text)
    if len(stripped.split()) > NOTE_WORDS:
        return False
    return bool(re.search(pattern, fold_key(stripped).strip()))


def _cell_number(text: str) -> float | None:
    """A schedule cell counts only if it is a number (with an optional unit), not a code like ME-2100."""
    m = _CELL_NUM.match(text.replace("\n", " "))
    return float(m.group(1).replace(",", ".")) if m else None


_LIST_NUMBER = re.compile(r"^\s*\d{1,2}\s*[.)]\s*(?=[^\d\s])")


def _own_numbers(text: str) -> list[float]:
    """Numbers written after the label in the same text: 'Cəmi 1360.80'. A leading '4.' is note numbering."""
    text = _LIST_NUMBER.sub("", text)
    return [float(m.group(0).split()[0].replace(",", ".")) for m in _STANDALONE_NUM.finditer(text)
            if re.match(r"[-+]?\d", m.group(0))]


def _pick(nums, pick):
    if not nums:
        return None
    try:
        return nums[pick]
    except IndexError:
        return None


def table_row(rule) -> Value:
    rule = _params(rule)
    pat = rule["anchor"]
    region_title = rule.get("region_title")
    near = rule.get("near")
    cands = []
    for sha in _files_for(rule):
        all_texts = L.dump(sha)["texts"]
        for t, region in L.texts_in(sha, rule["building"], region_title):
            if not _anchor_match(pat, t["text"]):
                continue
            if near and not any(re.search(near, fold_key(o["text"])) for o, rr in L.texts_in(sha, rule["building"])
                                if rr and region and rr["id"] == region["id"]):
                continue
            own = _own_numbers(t["text"])
            row = [o for o in L.row_of(t, all_texts, tol=rule["row_tol"], max_dx=_reach(t, rule["row_reach"]))
                   if o is not t]
            cells = [(o, _cell_number(o["text"])) for o in row]
            nums = own + [v for _, v in cells if v is not None]
            v = _pick(nums, rule["pick"])
            if v is None:
                continue
            used = [o for o, x in cells if x is not None and abs(x - v) < 1e-9][:1]
            cands.append((v, [L.dxf_source(sha, t, region, "row label")] + [L.dxf_source(sha, o, region) for o in used]))
    for sha in _pdfs_for(rule):
        for page in L.pdf(sha)["pages"]:
            if page.get("building") != rule["building"]:
                continue
            if region_title and not re.search(region_title, fold_key(" ".join(l["text"] for l in page["lines"][:400]))):
                continue
            for line in page["lines"]:
                if not _anchor_match(pat, line["text"]):
                    continue
                x0, y0, x1, y1 = line["bbox"]
                h = y1 - y0
                own = _own_numbers(line["text"])
                row = sorted((l for l in page["lines"] if l is not line and abs((l["bbox"][1] + l["bbox"][3]) / 2 - (y0 + y1) / 2) <= h * 0.6
                              and l["bbox"][0] >= x0), key=lambda l: l["bbox"][0])
                nums = own + [v for l in row for v in [_cell_number(l["text"])] if v is not None]
                v = _pick(nums, rule["pick"])
                if v is None:
                    continue
                cands.append((v, [L.pdf_source(sha, page["page"], line)]))
    if not cands:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), f"no row labelled /{pat}/", Method.SCHEDULE)
    values = Counter(round(v, 4) for v, _ in cands)
    best = values.most_common(1)[0][0]
    srcs = [s for v, ss in cands if round(v, 4) == best for s in ss]
    others = [{"value": v, "sources": [s.to_dict() for s in ss][:2]} for v, ss in cands if round(v, 4) != best]
    kinds = {s.locator["kind"] for s in srcs}
    return _value(rule, best, srcs, Method.SCHEDULE, verified=len(kinds) > 1 or values[best] > 1,
                  conflicts=others[:5])


def text_value(rule) -> Value:
    flags = re.IGNORECASE
    pat = re.compile(rule["pattern"], flags)
    cands = []
    for sha in _files_for(rule):
        for t, region in L.texts_in(sha):
            # Site notes sit on master-plan sheets whose stamps name the depot; only buildings filter.
            if rule.get("building") not in (None, "site") and region is not None and region["building"] != rule["building"]:
                continue
            text = fold_key(t["text"]) if rule.get("fold") else t["text"]
            m = pat.search(text)
            if m:
                cands.append((float(m.group(1).replace(",", ".")), L.dxf_source(sha, t, region, "note")))
    for sha in _pdfs_for(rule):
        for page in L.pdf(sha)["pages"]:
            if page.get("building") not in (rule.get("building"), None):
                continue
            for line in page["lines"]:
                text = fold_key(line["text"]) if rule.get("fold") else line["text"]
                m = pat.search(text)
                if m:
                    cands.append((float(m.group(1).replace(",", ".")), L.pdf_source(sha, page["page"], line)))
    if not cands:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), f"no text matching /{rule['pattern']}/", Method.STATED)
    values = Counter(round(v, 4) for v, _ in cands)
    best = values.most_common(1)[0][0]
    srcs = [s for v, s in cands if round(v, 4) == best]
    others = [{"value": v, "source": s.to_dict()} for v, s in cands if round(v, 4) != best]
    kinds = {s.locator["kind"] for s in srcs}
    return _value(rule, best, srcs, Method.STATED, verified=len(kinds) > 1, conflicts=others[:5])


_logged_tanks: set[str] = set()


def tank_part(rule) -> Value:
    """One concrete row (cover, bottom, or one wall) from a tank material table."""
    from .tanks import read_tank
    shas = _files_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the tank drawing is not in the register",
                       Method.SCHEDULE)
    data = read_tank(shas[0], rule["building"])
    if shas[0] not in _logged_tanks:
        _logged_tanks.add(shas[0])
        from .. import runlog
        for drop in data["dropped"]:
            runlog.warn("takeoff", f"dropped material anchor {drop['anchor']!r} ({drop['why']})", item=rule["id"])
    row = data["rows"].get(rule["role"])
    if row is None:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), f"no {rule['role']} concrete row", Method.SCHEDULE)
    sources = [L.dxf_source(shas[0], row["anchor"], row["region"], "material row"),
               L.dxf_source(shas[0], row["value_text"], row["region"], "volume")]
    note = row["title"]
    if row["per_element"]:
        note += "; 1 ədəd üçün"
    if row["conflict"]:
        return _value(rule, row["value"], sources, Method.SCHEDULE, note=note,
                      conflicts=({"value": row["value"], "source": sources[0].to_dict()},))
    return _value(rule, row["value"], sources, Method.SCHEDULE, note=note)


def tank_sum(rule) -> Value:
    """Bottom plus walls. A per-element wall is multiplied only by a count the drawing states."""
    from ..values import derive as derive_value
    from .tanks import read_tank
    shas = _files_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the tank drawing is not in the register",
                       Method.DERIVED)
    data = read_tank(shas[0], rule["building"])
    bottom = tank_part({**rule, "role": "bottom", "id": rule["id"] + "_bottom"})
    wall = tank_part({**rule, "role": "wall", "id": rule["id"] + "_wall"})
    if bottom.blocked or wall.blocked:
        return blocked(rule["unit"], [rule["id"]], _searched(rule),
                       "the bottom or the wall row was not read", Method.DERIVED)
    per = (data["rows"].get("wall") or {}).get("per_element")
    if not per:
        return derive_value("m³", "bottom_m3 + wall_m3", lambda bottom_m3, wall_m3: bottom_m3 + wall_m3,
                            bottom_m3=bottom, wall_m3=wall)
    count = data["count"]
    if count is None:
        return blocked(rule["unit"], ["Md-1 wall count"], _searched(rule), data["count_note"], Method.DERIVED)
    marks = [L.dxf_source(shas[0], t, L.region_of(shas[0], t["at"]), "Md-1") for t in count["marks"]]
    if marks:
        marks[0].locator["row"] = "Monolit divar"
        marks[0].locator["col"] = "Miq."
    count_value = Value(float(count["n"]), "each", Method.STATED, Status.EXTRACTED, sources=tuple(marks),
                        note=data["count_note"])
    return derive_value("m³", "bottom_m3 + wall_m3 × count",
                        lambda bottom_m3, wall_m3, count: bottom_m3 + wall_m3 * count,
                        bottom_m3=bottom, wall_m3=wall, count=count_value)


def sum_pattern(rule) -> Value:
    pat = rule["pattern"]
    seen, parts = set(), []
    for sha in _files_for(rule):
        all_texts = L.dump(sha)["texts"]
        for t, region in L.texts_in(sha, rule["building"]):
            if not _anchor_match(pat, t["text"]):
                continue
            own = [v for v in _own_numbers(re.sub(r"(?i)b\s*\d+", " ", t["text"]))]
            row = [o for o in L.row_of(t, all_texts, tol=READ_DEFAULTS["row_tol"], max_dx=_reach(t, READ_DEFAULTS["row_reach"]))
                   if o is not t]
            nums = own + [v for o in row for v in [_cell_number(o["text"])] if v is not None and re.search(r"m³|m3", o["text"])]
            if not nums:
                continue
            key = (region["id"] if region else None, round(nums[0], 3))
            if key in seen:
                continue
            seen.add(key)
            parts.append((nums[0], L.dxf_source(sha, t, region, "material table")))
    if not parts:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), f"no material rows /{pat}/", Method.SCHEDULE)
    total = sum(v for v, _ in parts)
    return _value(rule, total, [s for _, s in parts], Method.SCHEDULE,
                  note=f"sum of {len(parts)} material-table rows: " + " + ".join(f"{v:g}" for v, _ in parts))


def _schedule_tables(sha: str) -> tuple[list, str]:
    import json

    from .. import config
    name = L.files()[sha]["rel"]
    path = config.CACHE_DIR / "pdf" / f"{sha[:12]}.schedules.json"
    if not path.exists():
        return [], name
    return json.loads(path.read_text(encoding="utf-8")).get("tables") or [], name


def finish_sum(rule) -> Value:
    """Sum finish-schedule cells of one side and kind (ceiling paint, basement walls, and so on)."""
    from ..schedules.finishes import finish_areas, finish_sum as summarise
    shas = _pdfs_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the finish-schedule PDF is not in the register",
                       Method.SCHEDULE)
    tables, name = _schedule_tables(shas[0])
    if not tables:
        return blocked(rule["unit"], [rule["id"]], [name], "the schedule tables have not been read yet", Method.SCHEDULE)
    page = rule.get("page")
    if page is not None:
        tables = [t for t in tables if t["page"] == page]
    return summarise(finish_areas(tables), rule, shas[0], name)


def layer_measure(rule) -> Value:
    """A floor-schedule area times a thickness or a kg/m² printed in that row's layers."""
    from ..schedules.layers import floor_rows, layer_measure as measure
    shas = _pdfs_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the floor-schedule PDF is not in the register",
                       Method.SCHEDULE)
    tables, name = _schedule_tables(shas[0])
    if not tables:
        return blocked(rule["unit"], [rule["id"]], [name], "the schedule tables have not been read yet", Method.SCHEDULE)
    page = rule.get("page")
    if page is not None:
        tables = [t for t in tables if t["page"] == page]
    return measure(floor_rows(tables), rule, shas[0], name)


def window_openings(rule) -> Value:
    """Opening area from a window schedule: each mark's width × height × count, in m²."""
    from ..schedules.openings import opening_rows, openings_area
    shas = _pdfs_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the window-schedule PDF is not in the register",
                       Method.SCHEDULE)
    sha = shas[0]
    tables, name = _schedule_tables(sha)
    if not tables:
        return blocked(rule["unit"], [rule["id"]], [name], "the schedule tables have not been read yet", Method.SCHEDULE)
    rows = opening_rows(tables)
    page = rule.get("page")
    if page is not None:
        rows = [r for r in rows if r["page"] == page]
    if not rows:
        return blocked(rule["unit"], [rule["id"]], [name], "no window schedule rows on that sheet", Method.SCHEDULE)
    return openings_area(rows, rule["marks"], sha, name)


def door_openings(rule) -> Value:
    """Door area from the door schedule: every row of one material, width × height × count."""
    from ..schedules.openings import opening_rows, openings_area
    shas = _pdfs_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the door-schedule PDF is not in the register",
                       Method.SCHEDULE)
    sha = shas[0]
    tables, name = _schedule_tables(sha)
    if not tables:
        return blocked(rule["unit"], [rule["id"]], [name], "the schedule tables have not been read yet", Method.SCHEDULE)
    rows = opening_rows(tables)
    page = rule.get("page")
    if page is not None:
        rows = [r for r in rows if r["page"] == page]
    want = fold_key(rule.get("material") or "")
    chosen = []
    for row in rows:
        if not (row["mark"].startswith("Q-") and want and want in fold_key(row.get("material") or "")):
            continue
        if not row["B"] or not row["H"]:
            continue
        opening = row["B"] * row["H"] / 1_000_000
        if rule.get("max_opening_m2") is not None and opening > rule["max_opening_m2"]:
            continue
        if rule.get("min_opening_m2") is not None and opening <= rule["min_opening_m2"]:
            continue
        chosen.append(row)
    if not chosen:
        return blocked(rule["unit"], [rule["id"]], [name], f"no {rule.get('material')} door rows", Method.SCHEDULE)
    broken = [r["mark"] for r in chosen if r["conflict"]]
    if broken:
        return blocked(rule["unit"], broken, [name], "; ".join(r["conflict"] for r in chosen if r["conflict"]),
                       Method.SCHEDULE)
    return openings_area(rows, [r["mark"] for r in chosen], sha, name)


def window_sills(rule) -> Value:
    """Sill area from the size printed beside each Pa mark: length × depth × the row's count."""
    from ..schedules.openings import opening_rows, sills_area
    shas = _pdfs_for(rule)
    if not shas:
        return blocked(rule["unit"], [rule["id"]], _searched(rule), "the window-schedule PDF is not in the register",
                       Method.SCHEDULE)
    sha = shas[0]
    tables, name = _schedule_tables(sha)
    if not tables:
        return blocked(rule["unit"], [rule["id"]], [name], "the schedule tables have not been read yet", Method.SCHEDULE)
    rows = opening_rows(tables)
    page = rule.get("page")
    if page is not None:
        rows = [r for r in rows if r["page"] == page]
    return sills_area(rows, sha, name)


def run_rule(rule, done: dict) -> Value:
    t = rule["type"]
    if t == "dimension_max_h":
        return dimension_extreme(rule, horizontal=True)
    if t == "dimension_max_v":
        return dimension_extreme(rule, horizontal=False)
    if t == "dimension_mode":
        return dimension_mode(rule)
    if t == "slab_level_step":
        return slab_level_step(rule)
    if t == "floor_level_depth":
        return floor_level_depth(rule)
    if t == "table_row":
        return table_row(rule)
    if t == "text_value":
        return text_value(rule)
    if t == "sum_pattern":
        return sum_pattern(rule)
    if t == "tank_part":
        return tank_part(rule)
    if t == "tank_sum":
        return tank_sum(rule)
    if t == "window_openings":
        return window_openings(rule)
    if t == "door_openings":
        return door_openings(rule)
    if t == "window_sills":
        return window_sills(rule)
    if t == "layer_measure":
        return layer_measure(rule)
    if t == "finish_sum":
        return finish_sum(rule)
    if t == "derived":
        inputs = {name: done[spec["from"]] for name, spec in rule["inputs"].items()}
        names = list(inputs)
        return derive(rule["unit"], rule["formula"], lambda **kw: eval_product(kw, names), **inputs)
    if t == "not_implemented":
        note = (rule.get("searched") or ["no measurement method for this value yet"])[-1]
        return blocked(rule["unit"], [rule["id"]], rule.get("searched", []), note, Method.GEOMETRY)
    raise ValueError(f"unknown rule type {t}")


def eval_product(kw: dict, names: list[str]) -> float:
    result = 1.0
    for n in names:
        result *= kw[n]
    return result
