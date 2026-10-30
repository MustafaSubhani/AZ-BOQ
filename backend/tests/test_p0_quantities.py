"""P0 quantity bugs: a group total is not a line quantity, and a missing measurement is not the bill's number."""
import pytest

from azboq.match.run import _derived


def test_a_copy_is_not_derived_from_the_bill_quantity():
    lines = [
        {"id": "1.1", "section": "1.1", "unit": "m", "qty": 10, "description": "parent"},
        {"id": "1.2", "section": "1.1", "unit": "m", "qty": 10, "description": "əlavə the same pass"},
    ]
    out = {"1.1": {"status": "printed", "our_qty": None}, "1.2": {"status": "pending"}}
    _derived(lines, out)
    assert out["1.2"]["status"] == "pending"
    assert out["1.2"].get("our_qty") is None


def test_tonnes_before_the_volume_still_inherit_it():
    lines = [
        {"id": "1.1.2", "section": "1.1", "unit": "t", "qty": 18, "description": "haul"},
        {"id": "1.1.4", "section": "1.1", "unit": "m³", "qty": 10, "description": "cut"},
    ]
    out = {
        "1.1.2": {"status": "not_found", "our_qty": None},
        "1.1.4": {"status": "printed", "our_qty": 10},
    }
    _derived(lines, out)
    assert out["1.1.2"]["status"] == "derived"
    assert out["1.1.2"]["our_qty"] == 18
    assert out["1.1.2"]["derived_from"] == "1.1.4"
    lines = [
        {"id": "1.1", "section": "1.1", "unit": "m³", "qty": 10, "description": "cut"},
        {"id": "1.2", "section": "1.1", "unit": "t", "qty": 17.5, "description": "haul"},
    ]
    out = {"1.1": {"status": "printed", "our_qty": 9.5}, "1.2": {"status": "pending"}}
    _derived(lines, out)
    assert out["1.2"]["status"] == "derived"
    assert out["1.2"]["density"] == 1.75
    assert out["1.2"]["our_qty"] == 16.6  # 9.5 × 1.75, rounded to the bill's one decimal
