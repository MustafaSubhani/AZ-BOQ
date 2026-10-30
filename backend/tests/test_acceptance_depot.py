"""The depot acceptance rows. The number is the engine's result, with its source named in the audit."""
import pytest

from azboq import store

pytestmark = pytest.mark.skipif(store.get("report") is None, reason="the check has not been run")


def _row(line_id):
    return store.get("report")["lines"][line_id]


def _qty(line_id, status, qty):
    row = _row(line_id)
    assert row["status"] == status
    assert row["our_qty"] == pytest.approx(qty)


def _floor(line_id, floor):
    floors = store.get("floors")
    if not floors:
        pytest.skip("floors have not been built")
    assert floors["lines"][line_id]["floor"] == floor


def test_false_matches_are_not_accepted():
    for line_id in ("12.1.2", "13.1.2", "2.13.6", "2.13.11", "2.13.12", "2.20.17", "2.7.27", "12.1.25"):
        assert _row(line_id)["status"] not in ("matched", "printed")
    _qty("2.6.7", "matched", 252.276)
    _qty("2.5.19", "printed", 9)
    assert _row("2.5.13")["our_qty"] == pytest.approx(190.5)
    assert _row("2.5.14")["our_qty"] == pytest.approx(154.2)
    assert "nov" in _row("2.5.13")["reason"]
    assert _row("2.5.13")["status"] == "different"
    assert _row("2.5.14")["status"] == "different"
    assert "1st floor, type 2" in _row("2.7.14")["reason"]
    assert "floor_1" not in _row("2.7.14")["reason"]


def test_roof_windows_and_openings():
    _qty("2.5.19", "printed", 9)
    _qty("2.6.7", "matched", 252.276)
    _qty("2.6.8", "matched", 2.88)
    _qty("2.6.10", "matched", 38.988)
    _qty("2.6.11", "matched", 37.52)


def test_basement_floors_and_the_garage_conflict():
    _qty("2.7.1", "printed", 1344)
    _qty("2.7.2", "printed", 1344)
    _floor("2.7.1", "basement")
    _qty("2.7.3", "matched", 1.533)
    for line_id in ("2.7.6", "2.7.7", "2.7.8", "2.7.9", "2.7.10", "2.7.11"):
        _qty(line_id, "printed", 43.8)
        _floor(line_id, "basement")
    assert _row("2.7.12")["status"] == "review" and _row("2.7.12")["our_qty"] is None
    assert _row("2.7.13")["status"] == "review"
    assert "658.30" in _row("2.7.12")["reason"] and "665.3" in _row("2.7.12")["reason"]
    assert "665.3" in _row("2.7.12")["reason"] and "hatch" in _row("2.7.12")["reason"]
    reasons = _row("2.6.7").get("review_reasons") or []
    assert any(r.get("code") == "hand_link" for r in reasons)


def test_first_floor_groups():
    for line_id in ("2.7.14", "2.7.17", "2.7.18", "2.7.19", "2.7.21"):
        _qty(line_id, "different", 129)
        _floor(line_id, "floor_1")
    assert _row("2.7.15")["status"] == "review"
    assert _row("2.7.15")["our_qty"] == pytest.approx(103.2)
    for line_id in ("2.7.22", "2.7.25", "2.7.26", "2.7.28"):
        _qty(line_id, "printed", 230.6)
    assert _row("2.7.23")["status"] == "review"
    assert _row("2.7.24")["status"] == "review"
    assert _row("2.7.24")["our_qty"] == pytest.approx(12.9136)
    _qty("2.7.29", "printed", 104.6)
    _qty("2.7.30", "matched", 7.322)
    _qty("2.7.31", "matched", 0.14121)
    _qty("2.7.32", "matched", 0.14121)
    _qty("2.7.36", "printed", 188.2)
    _qty("2.7.37", "matched", 13.174)
    _qty("2.7.38", "matched", 0.25407)
    _qty("2.7.39", "matched", 0.25407)
    for line_id in ("2.7.46", "2.7.47", "2.7.48"):
        _qty(line_id, "printed", 39)
        _floor(line_id, "floor_1")


def test_second_floor_groups():
    _qty("2.7.56", "printed", 538.4)
    _qty("2.7.61", "printed", 538.4)
    _floor("2.7.56", "floor_2")
    for line_id in ("2.7.65", "2.7.71"):
        _qty(line_id, "printed", 39)
        _floor(line_id, "floor_2")
    _qty("2.7.75", "printed", 160)
    _qty("2.7.78", "printed", 35.4)
    _floor("2.7.75", "floor_2")
    _floor("2.7.78", "floor_2")


def test_finishes():
    row = _row("2.8.1")
    assert row["status"] == "different"
    assert row["our_qty"] == pytest.approx(1368.7)
    assert row["gap"] == pytest.approx(-35.1)
    _qty("2.8.4", "matched", 96)
    _qty("2.8.5", "matched", 96)
    _qty("2.8.7", "different", 3380)
    _qty("2.8.8", "different", 3380)
    assert _row("2.8.11")["status"] == "not_found"
    assert _row("2.8.12")["status"] == "review" and _row("2.8.12")["our_qty"] is None
    assert "370" in _row("2.8.12")["reason"]


def test_window_glass_explanation_names_each_mark():
    from azboq.match.explain import explain_line
    data = explain_line("2.6.7", store.get("bill"), store.get("report"), store.get("takeoff"))
    assert data and data["item"]
    rows = {src["row"] for item in data["inputs"] for src in item["sources"]}
    assert {"P-1", "P-2", "P-3", "P-4"} <= rows
    assert "252.276" in (data["item"]["substituted"] or "")
    assert all(item["label"] != item["name"] for item in data["inputs"])
    for line_id in ("10.1.24", "11.1.24"):
        _qty(line_id, "matched", 4.13)
    for line_id in ("10.1.15", "11.1.15"):
        _qty(line_id, "matched", 27.73)
    for line_id in ("12.1.13", "13.1.13"):
        _qty(line_id, "matched", 14.49)
    for line_id in ("12.1.22", "13.1.22"):
        _qty(line_id, "matched", 1.58)
    assert _row("19.1.3")["our_qty"] == pytest.approx(383.7)
    assert _row("20.1.3")["our_qty"] == pytest.approx(216)
    _qty("3.5.7", "printed", 12.8)
    sheets = " ".join(str((src.get("sheet") or "")) for src in _row("3.5.7").get("sources") or [])
    assert "9335-08-MT" in sheets
    assert "9336" not in sheets


def test_hand_links_carry_a_review_reason():
    from azboq.rules import load
    report = store.get("report")
    for row in load("bill_map"):
        for line_id in row["lines"]:
            reasons = (report["lines"].get(line_id) or {}).get("review_reasons") or []
            assert any(item.get("code") == "hand_link" for item in reasons), line_id


def test_mesh_weight_and_tank_count_name_their_cells():
    from azboq.match.explain import explain_line
    bill, report, takeoff = store.get("bill"), store.get("report"), store.get("takeoff")
    mesh = explain_line("2.7.38", bill, report, takeoff)
    printed = [src.get("printed") or "" for item in mesh["inputs"] for src in item["sources"]]
    assert any("1.35" in text for text in printed)
    tank = explain_line("10.1.15", bill, report, takeoff)
    count = next(item for item in tank["inputs"] if item["sources"] and item["sources"][0].get("col") == "Miq.")
    assert count["sources"][0]["handle"]
    assert "Miq" in count["label"]
