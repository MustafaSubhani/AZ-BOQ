"""The same room printed with two areas.

The floor-type schedule and the finish schedule each give room 1 on the 1st
floor an area. When those areas differ, the bill lines for that floor are review:
the engine does not pick one of them.
"""
import re

from ..text.normalise import fold_key


def _area_cell(row: dict) -> dict | None:
    for cell in row.get("cells") or []:
        text = (cell.get("text") or "").strip().replace(" ", "")
        if cell.get("unit") == "m²" and re.fullmatch(r"\d+(?:[.,]\d+)?", text):
            return cell
    return None


def _floor_rooms(row: dict) -> list[str]:
    rooms = []
    for cell in row.get("cells") or []:
        if "otaq" not in fold_key(cell.get("header") or ""):
            continue
        rooms.extend(re.findall(r"\d+", cell.get("text") or ""))
    return rooms


def _finish_rooms(row: dict) -> list[str]:
    rooms = []
    for cell in row.get("cells") or []:
        header = fold_key(cell.get("header") or "")
        if "tipi" in header or cell.get("unit"):
            continue
        if re.fullmatch(r"\d{1,2}", (cell.get("text") or "").strip()):
            rooms.append(cell["text"].strip())
    return rooms


def _is_finish(table: dict) -> bool:
    blob = fold_key(table.get("title", "") + " " + " ".join(c.get("header") or "" for c in table.get("columns") or []))
    return "bezek" in blob or ("tavan" in blob and "divar" in blob)


def _is_floor(table: dict) -> bool:
    blob = fold_key(table.get("title", "") + " " + " ".join(c.get("header") or "" for c in table.get("columns") or []))
    return ("doseme" in blob or "eksplik" in blob) and "bezek" not in blob


def same_room_conflicts(tables: list[dict], rooms: list[dict] | None = None) -> list[dict]:
    """One room, one floor, two schedule areas."""
    floor_hits = []
    finish_hits = []
    for table in tables:
        for row in table.get("rows") or []:
            if row.get("section") or not row.get("floor"):
                continue
            area = _area_cell(row)
            if area is None:
                continue
            item = {"floor": row["floor"], "page": table.get("page"),
                    "value": float(area["text"].replace(",", ".").replace(" ", "")),
                    "text": area["text"].strip(), "cell": area}
            if _is_floor(table):
                if _floor_rooms(row) == ["1"]:
                    floor_hits.append(item)
            elif _is_finish(table):
                if _finish_rooms(row) == ["1"]:
                    finish_hits.append(item)
    names = {"basement": "the basement", "floor_1": "the 1st floor", "floor_2": "the 2nd floor"}
    out = []
    for floor in floor_hits:
        for finish in finish_hits:
            if floor["floor"] != finish["floor"] or abs(floor["value"] - finish["value"]) <= 0.05:
                continue
            where = names.get(floor["floor"], floor["floor"])
            parts = [f"{floor['text']} m² on the floor schedule"]
            room = _room_one(rooms or [], floor["floor"])
            if room:
                parts.append(f"{room['text']} m² on the room schedule ({room['name']})")
            parts.append(f"{finish['text']} m² on the finish schedule")
            out.append({
                "id": f"room-1-{floor['floor']}",
                "floor": floor["floor"],
                "room": "1",
                "areas": [floor, finish],
                "text": f"room 1 on {where} is " + ", ".join(parts),
            })
    return out


def _room_one(rooms: list[dict], floor: str) -> dict | None:
    for schedule in rooms:
        if schedule.get("floor") != floor:
            continue
        for row in schedule.get("rows") or []:
            if row.get("room") == "1":
                return row
    return None


def cemi_conflicts(rooms: list[dict]) -> list[dict]:
    names = {"basement": "Basement", "floor_1": "1st floor", "floor_2": "2nd floor"}
    out = []
    for item in rooms:
        gap = item.get("gap")
        if gap is None or abs(gap) <= 0.05:
            continue
        where = names.get(item["floor"], item["floor"])
        out.append({
            "id": f"cemi-{item['floor']}",
            "text": (f"{where} rooms sum to {item['sum']:g} m²; "
                     f"the schedule prints Cəmi {item.get('total_text')} m²"),
        })
    return out
