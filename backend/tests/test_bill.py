import pytest

from azboq import config
from azboq.bill.parse import parse_bill

pytestmark = pytest.mark.skipif(not config.BILL_PATH.exists(), reason="client bill not present")


@pytest.fixture(scope="module")
def bill():
    return parse_bill()


def test_counts(bill):
    top = [s for s in bill["sections"] if not s.get("parent")]
    children = [s for s in bill["sections"] if s.get("parent")]
    assert len(top) == 132
    assert len(children) == 13
    assert len(bill["lines"]) == 2175
    assert all(l["qty"] and l["qty"] > 0 for l in bill["lines"])


def test_retaining_wall_subsections(bill):
    walls = [s for s in bill["sections"] if s.get("mark")]
    assert [s["mark"] for s in walls] == [f"İD-{i}" for i in range(1, 14)]
    assert all(s["parent"] == "25.1" and s["code"] == f"25.1.{i}" for i, s in enumerate(walls, start=1))
    assert all(len(s["lines"]) == 7 for s in walls)
    assert all(s["trade"] != "earthworks" for s in walls)
    assert all(not line["id"].startswith("25.1.r") for line in bill["lines"])


def test_building_is_inherited_when_the_title_names_none(bill):
    by_code = {s["code"]: s for s in bill["sections"]}
    assert by_code["9.13"]["building"] == "heating_point"
    assert by_code["24.1"]["building"] == "sand_pit"


def test_totals_chain_to_the_cent(bill):
    assert round(bill["line_sum"], 2) == 3110505.89
    assert round(bill["chain"]["total"], 2) == 3811193.36
    assert round(bill["totals"]["total"], 2) == 3811193.36
    assert round(bill["totals"]["contract_price_c5"], 2) == 3811193.36


def test_codes_repaired_by_position(bill):
    codes = [s["code"] for s in bill["sections"]]
    assert "2.10" in codes and "2.1" in codes and "2.20" in codes and "14.10" in codes
    s210 = next(s for s in bill["sections"] if s["code"] == "2.10")
    assert s210["stored_code"] == 2.1 and s210["code_repaired"]


def test_units_and_unknown_ff(bill):
    units = {l["unit"] for l in bill["lines"]}
    assert {"m³", "m²", "m", "each", "t", "set", "km", "kg"} <= units
    assert len(bill["unknown_units"]) == 1


def test_reviewer_comments_attached(bill):
    commented = [l for l in bill["lines"] if l["comment"]]
    assert len(commented) >= 9
    assert any("addendum 15" in l["comment"] for l in commented)
