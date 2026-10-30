"""Hatch outlines linked to a room, and the area book those rooms feed.

A hatch with no room number inside it stays visible as an unlinked area.
Copies of a sheet are not measured again.
"""
import json
import re

from shapely.geometry import Point, Polygon

from . import config
from .floors import classify
from .text.normalise import fold_key

_ROOM = re.compile(r"^\d{1,2}\*?$")

def _floor_of(region: dict, texts: list[dict]) -> str | None:
    """The sheet title, or the only floor named in the text on that sheet."""
    named = classify(region.get("title") or "")
    if named:
        return named
    counts: dict[str, int] = {}
    for text in texts:
        floor = classify(text.get("text") or "")
        if floor:
            counts[floor] = counts.get(floor, 0) + 1
    if len(counts) == 1:
        return next(iter(counts))
    return None


def link_hatches_to_rooms(hatches: list[dict], texts: list[dict], rooms_by_number: dict) -> dict:
    """One room tag inside a hatch links that hatch. Two tags is a conflict, not a guess."""
    tags = [t for t in texts if _ROOM.fullmatch((t.get("text") or "").strip()) and t.get("at")]
    out = {}
    for hatch in hatches:
        ring = _outer(hatch)
        if ring is None or not hatch.get("handle"):
            continue
        try:
            poly = Polygon(ring, hatch.get("holes") or [])
            if not poly.is_valid:
                poly = poly.buffer(0)
        except Exception:
            continue
        inside = []
        for tag in tags:
            try:
                if poly.contains(Point(tag["at"][0], tag["at"][1])):
                    inside.append(tag["text"].strip().replace("*", ""))
            except Exception:
                continue
        names = list(dict.fromkeys(inside))
        rooms = [rooms_by_number[n] for n in names if n in rooms_by_number]
        if len(names) == 1 and rooms:
            room = rooms[0]
            out[hatch["handle"]] = {**room, "kind": "room", "hatch_area_du2": hatch.get("area_du2")}
        elif len(names) > 1:
            out[hatch["handle"]] = {
                "kind": "area_conflict", "rooms": names, "label": "rooms " + ", ".join(names),
                "hatch_area_du2": hatch.get("area_du2"),
            }
    return out


def metres_per_unit(takeoff: dict | None) -> float | None:
    """Drawing units to metres, from the depot gate: the printed dimension over the measured metres."""
    item = next((row for row in (takeoff or {}).get("items") or [] if row.get("id") == "gate_long"), None)
    value = ((item or {}).get("value") or {}).get("value")
    if not value:
        return None
    for source in (item["value"].get("sources") or []):
        measured = (source.get("locator") or {}).get("measurement")
        if measured:
            return float(value) / float(measured)
    return None


def region_shapes(sha: str, region_id: str, meta: dict, takeoff: dict | None, report: dict | None) -> dict:
    """Outlines on one sheet, in image pixels, each with the room it sits on."""
    region = meta.get("region") or {}
    if region.get("copy_of"):
        order = region.get("only_other_order") or region.get("copy_of")
        return {"shapes": [], "banner": f"This sheet is a copy ({order}). Outlines are on the original.",
                "transform": meta.get("transform")}
    transform = meta.get("transform") or {}
    if transform.get("kind") != "dxf" or not transform.get("bbox") or not transform.get("offset"):
        return {"shapes": [], "transform": transform}
    x0, y0, x1, y1 = transform["bbox"]
    scale = transform["scale"]
    ox, oy = transform["offset"]

    def px(point):
        return [ox + (point[0] - x0) * scale, oy + (y1 - point[1]) * scale]

    from .dwg.read import geom_path_for, load_dump
    geom_path = geom_path_for(sha)
    if not geom_path.exists():
        return {"shapes": [], "transform": transform}
    hatches = json.loads(geom_path.read_text(encoding="utf-8")).get("hatches") or []
    on_sheet = [h for h in hatches if h.get("at") and x0 <= h["at"][0] <= x1 and y0 <= h["at"][1] <= y1 and _outer(h)]
    dump = load_dump(sha) or {}
    texts = [t for t in dump.get("texts") or [] if t.get("at") and x0 <= t["at"][0] <= x1 and y0 <= t["at"][1] <= y1]
    floor = _floor_of(region, texts)
    rooms = _rooms_by_number(floor)
    linked = link_hatches_to_rooms(on_sheet, texts, rooms)
    per_unit = metres_per_unit(takeoff)
    shapes = []
    for hatch in on_sheet:
        link = linked.get(hatch["handle"]) or {}
        area = None
        if per_unit is not None and hatch.get("area_du2"):
            area = hatch["area_du2"] * per_unit * per_unit
        kind = link.get("kind") or "area_unlinked"
        schedule = link.get("schedule_m2")
        if kind == "room" and schedule and area and area > float(schedule) * 1.5:
            kind = "area_unlinked"
            link = {}
        label = link.get("label") or hatch.get("layer") or "area"
        lines = _lines_for(report, link.get("name") or "")
        shapes.append({
            "id": f"h:{hatch['handle']}",
            "kind": kind,
            "points": [px(p) for p in _outer(hatch)],
            "area_m2": None if area is None else round(area, 2),
            "label": label,
            "item": link.get("item"),
            "lines": lines,
            "status": "review" if kind == "area_conflict" or lines else None,
            "room": link.get("room"),
            "schedule_m2": link.get("schedule_m2"),
        })
    return {"shapes": shapes, "transform": transform, "floor": floor, "metres_per_unit": per_unit}


def area_book(register: dict, takeoff: dict | None, report: dict | None, sheets: dict | None = None) -> dict:
    """Rooms from the PDF room schedules, with a hatch area where a plan tag sits inside one."""
    per_unit = metres_per_unit(takeoff)
    hatches = _hatch_index(register, sheets or {}, per_unit)
    floors = []
    for path in sorted((config.CACHE_DIR / "pdf").glob("*.schedules.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for schedule in data.get("rooms") or []:
            rooms = []
            for row in schedule.get("rows") or []:
                hit = hatches.get((schedule.get("floor"), row.get("room")))
                rooms.append({
                    "room": row.get("room"),
                    "name": row.get("name"),
                    "room_schedule": row.get("area"),
                    "room_text": row.get("text"),
                    "hatch_m2": None if not hit else hit.get("area_m2"),
                    "lines": _lines_for(report, row.get("name") or ""),
                })
            floors.append({
                "floor": schedule.get("floor"),
                "file": data.get("file"),
                "page": schedule.get("page"),
                "total": schedule.get("total"),
                "total_text": schedule.get("total_text"),
                "sum": schedule.get("sum"),
                "gap": schedule.get("gap"),
                "rooms": rooms,
            })
    conflicts = (report or {}).get("drawing_conflicts") or []
    return {"floors": floors, "conflicts": conflicts}


def _outer(hatch: dict) -> list | None:
    outline = hatch.get("outline")
    if isinstance(outline, list) and outline and isinstance(outline[0], list) and len(outline[0]) >= 3:
        return outline[0]
    return None


def _rooms_by_number(floor: str | None) -> dict:
    if not floor:
        return {}
    found = {}
    for path in (config.CACHE_DIR / "pdf").glob("*.schedules.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for schedule in data.get("rooms") or []:
            if schedule.get("floor") != floor:
                continue
            for row in schedule.get("rows") or []:
                found[str(row.get("room"))] = {
                    "room": str(row.get("room")),
                    "name": row.get("name") or "",
                    "label": f"{row.get('room')} {row.get('name') or ''}".strip(),
                    "schedule_m2": row.get("area"),
                    "floor": floor,
                }
    return found


def _hatch_index(register: dict, sheets: dict, per_unit: float | None) -> dict:
    """Hatch area by (floor, room), measured only on the original plan of that floor."""
    sha = next((f["sha256"] for f in register.get("files") or []
                if f.get("kind") == "drawing_cad" and "(SON)" in (f.get("name") or "") and f.get("building") == "depot"), None)
    if sha is None or per_unit is None:
        return {}
    full = next((key for key in (sheets.get("dwg") or {}) if key.startswith(sha[:12])), None)
    if full is None:
        return {}
    from .dwg.read import geom_path_for, load_dump
    path = geom_path_for(sha)
    if not path.exists():
        return {}
    geom = json.loads(path.read_text(encoding="utf-8"))
    texts = (load_dump(sha) or {}).get("texts") or []
    out = {}
    for region in (sheets["dwg"][full].get("regions") or []):
        if region.get("copy_of"):
            continue
        box = region.get("bbox")
        if not box:
            continue
        x0, y0, x1, y1 = box
        here = [t for t in texts if t.get("at") and x0 <= t["at"][0] <= x1 and y0 <= t["at"][1] <= y1]
        floor = _floor_of(region, here)
        if not floor:
            continue
        on_sheet = [h for h in geom.get("hatches") or []
                    if h.get("at") and x0 <= h["at"][0] <= x1 and y0 <= h["at"][1] <= y1 and _outer(h)]
        linked = link_hatches_to_rooms(on_sheet, here, _rooms_by_number(floor))
        used = set()
        rooms = _rooms_by_number(floor)
        for handle, link in linked.items():
            if link.get("kind") != "room":
                continue
            hatch = next((h for h in on_sheet if h.get("handle") == handle), None)
            area = None
            if hatch and hatch.get("area_du2"):
                area = round(hatch["area_du2"] * per_unit * per_unit, 2)
            schedule = link.get("schedule_m2")
            if schedule and area and area > float(schedule) * 1.5:
                continue
            out[(floor, str(link.get("room")))] = {"area_m2": area, "handle": handle}
            used.add(handle)
        for room_no, info in rooms.items():
            if (floor, str(room_no)) in out or not info.get("schedule_m2"):
                continue
            schedule = float(info["schedule_m2"])
            close = []
            for hatch in on_sheet:
                if hatch.get("handle") in used or not hatch.get("area_du2"):
                    continue
                area = round(hatch["area_du2"] * per_unit * per_unit, 2)
                if abs(area - schedule) / schedule <= 0.01:
                    close.append((hatch, area))
            if len(close) == 1:
                out[(floor, str(room_no))] = {"area_m2": close[0][1], "handle": close[0][0]["handle"]}
                used.add(close[0][0]["handle"])
    return out


def _lines_for(report: dict | None, name: str) -> list[str]:
    key = fold_key(name)
    if len(key) < 4 or not report:
        return []
    found = []
    for line_id, row in (report.get("lines") or {}).items():
        if key in fold_key(row.get("reason") or ""):
            found.append(line_id)
    return found[:8]
