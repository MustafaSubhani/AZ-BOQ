"""A build-up is a run of bill lines that share one area.

It starts at an m² line. Later m² lines stay in it when they repeat that area, or
when they are the 0.8 coverage the timber floors use. Anything else stays in the
run until the next area, so a floor written on the last line covers the run.
"""
from collections import defaultdict


def _decimals(qty: float) -> int:
    text = f"{float(qty):.6f}".rstrip("0").rstrip(".")
    return len(text.split(".")[1]) if "." in text else 0


def close_qty(a: float, b: float) -> bool:
    return abs(a - b) <= 0.5 * 10 ** -_decimals(b) + 1e-9


def same_area(qty: float, parent: float) -> bool:
    """Same area, or the 0.8 joist-coverage line (104 m² under a 130 m² floor)."""
    if not parent:
        return False
    if close_qty(qty, parent):
        return True
    return abs(qty / parent - 0.8) <= 0.01


def buildup_groups(lines: list[dict]) -> list[dict]:
    by_section = defaultdict(list)
    for line in lines:
        by_section[line["section"]].append(line)
    groups = []
    for sec_lines in by_section.values():
        current = None
        for line in sec_lines:
            if line.get("unit") == "m²" and line.get("qty"):
                if current is None or not same_area(line["qty"], current["qty"]):
                    current = {"qty": line["qty"], "lines": []}
                    groups.append(current)
            if current is not None:
                current["lines"].append(line)
    return groups
