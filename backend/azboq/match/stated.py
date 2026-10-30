"""Quantities a bill line states in its own description.

They explain the line and name the number to look for. They are not drawing evidence.
"""
import re

_PAREN = re.compile(r"\((\d[\d\s]*),(\d+)\s*(m²|m2|m³|m3|m)(?![²³\w])", re.I)
_QAL = re.compile(r"qal\s*=\s*(\d+(?:[.,]\d+)?)\s*(sm|mm|m)\b", re.I)
_UNIT = {"m2": "m²", "m²": "m²", "m3": "m³", "m³": "m³", "m": "m"}
_TO_M = {"mm": 0.001, "sm": 0.01, "m": 1.0}


def stated_quantity(text: str) -> dict | None:
    """'(1201,7 m², qal=20 sm)' → 1201.7 m² and a thickness of 0.20 m."""
    found = _PAREN.search(text or "")
    if not found:
        return None
    qty = float(found.group(1).replace(" ", "") + "." + found.group(2))
    unit = _UNIT[found.group(3).lower()]
    thick = _QAL.search(text or "")
    thickness_m = None
    if thick:
        thickness_m = float(thick.group(1).replace(",", ".")) * _TO_M[thick.group(2).lower()]
    return {"qty": qty, "unit": unit, "thickness_m": thickness_m}
