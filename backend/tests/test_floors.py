"""A storey is recorded only when the text names it."""
import pytest

from azboq import store
from azboq.floors import classify


def test_storey_words():
    assert classify("Zirzəminin planından fraqment") == "basement"
    assert classify("texniki döşəməaltı") == "basement"
    assert classify("1-ci mərtəbənin planı") == "floor_1"
    assert classify("I mərtəbə") == "floor_1"
    assert classify("Magistral şəbəkə.  2-ci mərtəbənin planı.") == "floor_2"
    assert classify("II mərtəbə") == "floor_2"
    assert classify("Mərtəbəarası dəmir beton tava") is None
    assert classify("Dam örtüyü") == "roof"
    assert classify("4 çıxışlı Yanğın Deposu binası  (Torpaq işləri)") is None
    assert classify("Örtük elementlərinin yerləşmə sxemi") is None


def test_a_floor_on_one_line_covers_the_build_up():
    from azboq.groups import buildup_groups, same_area
    lines = [
        {"id": "2.7.1", "section": "2.7", "unit": "m²", "qty": 1344, "description": "beton örtük"},
        {"id": "2.7.2", "section": "2.7", "unit": "m²", "qty": 1344, "description": "əlavə 5 mm (Zirzəmi)"},
        {"id": "2.7.3", "section": "2.7", "unit": "m³", "qty": 1.533, "description": "keramzit"},
        {"id": "2.7.6", "section": "2.7", "unit": "m²", "qty": 43.8, "description": "sement"},
        {"id": "2.7.11", "section": "2.7", "unit": "m²", "qty": 43.8, "description": "keramik (Zirzəmi)"},
        {"id": "2.7.14", "section": "2.7", "unit": "m²", "qty": 130, "description": "taxta"},
        {"id": "2.7.15", "section": "2.7", "unit": "m²", "qty": 104, "description": "izolyasiya"},
        {"id": "2.7.21", "section": "2.7", "unit": "m²", "qty": 130, "description": "lak (1-ci mərtəbə)"},
        {"id": "2.7.22", "section": "2.7", "unit": "m²", "qty": 230.6, "description": "laminat"},
    ]
    assert same_area(104, 130)
    assert not same_area(43.8, 1344)
    groups = buildup_groups(lines)
    assert [line["id"] for line in groups[0]["lines"]] == ["2.7.1", "2.7.2", "2.7.3"]
    assert groups[1]["qty"] == 43.8
    timber = next(g for g in groups if g["qty"] == 130)
    assert [line["id"] for line in timber["lines"]] == ["2.7.14", "2.7.15", "2.7.21"]
    assert groups[-1]["qty"] == 230.6


needs_bill = pytest.mark.skipif(store.get("bill") is None, reason="bill has not been read")


@needs_bill
def test_every_line_is_stated_or_unstated():
    from azboq.floors import UNSTATED, build_floors
    out = build_floors()
    bill = store.get("bill")
    assert set(out["lines"]) == {l["id"] for l in bill["lines"]}
    assert set(out["counts"]) <= {"basement", "floor_1", "floor_2", "floor_3", "roof", UNSTATED}
    assert out["counts"][UNSTATED] > out["counts"].get("basement", 0)


@needs_bill
def test_floor_comes_from_the_line_before_the_section():
    from azboq.floors import build_floors
    out = build_floors()
    stated = [v for v in out["lines"].values() if v["from"] == "line"]
    assert stated
    assert all(v["floor"] != "unstated" for v in stated)


@needs_bill
def test_one_floor_tag_covers_the_section_27_build_ups():
    from azboq.floors import build_floors
    out = build_floors()
    assert out["lines"]["2.7.1"] == {"floor": "basement", "from": "group"}
    assert out["lines"]["2.7.2"]["from"] == "line"
    assert out["lines"]["2.7.6"]["floor"] == "basement"
    assert out["lines"]["2.7.12"]["floor"] == "floor_1"
    assert out["lines"]["2.7.14"]["floor"] == "floor_1"
    assert out["lines"]["2.7.15"]["floor"] == "floor_1"


def test_group_copies_share_the_drawing_quantity():
    from azboq.match.run import _propagate_groups
    lines = [
        {"id": "a", "section": "2.7", "unit": "m²", "qty": 130, "description": "taxta"},
        {"id": "b", "section": "2.7", "unit": "m²", "qty": 104, "description": "izolyasiya"},
        {"id": "c", "section": "2.7", "unit": "m²", "qty": 130, "description": "lak (1-ci mərtəbə)"},
    ]
    out = {
        "a": {"status": "not_found", "our_qty": None, "reason": "no"},
        "b": {"status": "not_found", "our_qty": None, "reason": "no"},
        "c": {"status": "different", "our_qty": 129.0, "reason": "the schedule prints 129", "method": "schedule"},
    }
    _propagate_groups(lines, out)
    assert out["a"]["status"] == "different" and out["a"]["our_qty"] == 129
    assert out["a"]["group_from"] == "c"
    assert out["b"]["status"] == "not_found"


def test_joist_coverage_is_a_hint_not_a_measurement():
    from azboq.match.run import _coverage_hints
    lines = [
        {"id": "2.7.14", "section": "2.7", "unit": "m²", "qty": 130, "description": "laqa"},
        {"id": "2.7.15", "section": "2.7", "unit": "m²", "qty": 104, "description": "izolyasiya"},
        {"id": "2.7.22", "section": "2.7", "unit": "m²", "qty": 230.6, "description": "laqa"},
        {"id": "2.7.23", "section": "2.7", "unit": "m²", "qty": 184.5, "description": "izolyasiya"},
        {"id": "24.1.6", "section": "24.1", "unit": "m²", "qty": 26, "description": "qum"},
        {"id": "24.1.7", "section": "24.1", "unit": "m²", "qty": 21, "description": "qum"},
    ]
    out = {
        "2.7.14": {"status": "different", "our_qty": 129.0, "reason": "schedule"},
        "2.7.15": {"status": "not_found", "our_qty": None, "reason": "no"},
        "2.7.22": {"status": "printed", "our_qty": 230.6, "reason": "printed"},
        "2.7.23": {"status": "not_found", "our_qty": None, "reason": "no"},
        "24.1.6": {"status": "not_found", "our_qty": None, "reason": "no"},
        "24.1.7": {"status": "not_found", "our_qty": None, "reason": "no"},
    }
    _coverage_hints(lines, out)
    assert out["2.7.15"]["status"] == "review"
    assert out["2.7.15"]["our_qty"] == 103.2
    assert "2.7.23" in out["2.7.15"]["reason"]
    assert out["2.7.23"]["status"] == "review"
    assert out["2.7.23"]["our_qty"] == 184.48
    assert out["24.1.7"]["status"] == "not_found"


def test_polystyrene_on_the_coverage_area_uses_the_printed_thickness():
    from azboq.match.run import _volume_hints
    lines = [
        {"id": "2.7.22", "section": "2.7", "building": "depot", "unit": "m²", "qty": 230.6, "description": "laqa"},
        {"id": "2.7.23", "section": "2.7", "building": "depot", "unit": "m²", "qty": 184.5, "description": "izolyasiya"},
        {"id": "2.7.24", "section": "2.7", "building": "depot", "unit": "m³", "qty": 12.915, "description": "Penopolistrol plitələri"},
        {"id": "2.7.56", "section": "2.7", "building": "depot", "unit": "m²", "qty": 538.4, "description": "laminat"},
        {"id": "2.7.57", "section": "2.7", "building": "depot", "unit": "m²", "qty": 430.72, "description": "coverage"},
        {"id": "2.7.58", "section": "2.7", "building": "depot", "unit": "m³", "qty": 21.54, "description": "izolyasiya qumla"},
    ]
    out = {
        "2.7.22": {"status": "printed", "our_qty": 230.6, "reason": "printed"},
        "2.7.23": {"status": "review", "our_qty": 184.48, "reason": "coverage"},
        "2.7.24": {"status": "not_found", "our_qty": None, "reason": "no"},
        "2.7.56": {"status": "printed", "our_qty": 538.4, "reason": "printed"},
        "2.7.57": {"status": "review", "our_qty": 430.72, "reason": "coverage"},
        "2.7.58": {"status": "not_found", "our_qty": None, "reason": "no"},
    }
    rows = [{
        "building": "depot", "floor": "floor_1", "type_no": "3", "area": 230.6,
        "layers": [
            {"text": "penopolisterol - 70mm", "thickness_mm": 70},
            {"text": "yüngül beton - 50 mm", "thickness_mm": 50},
        ],
    }, {
        "building": "depot", "floor": "floor_2", "type_no": "1", "area": 538.4,
        "layers": [{"text": "yüngül beton - 50 mm", "thickness_mm": 50}],
    }]
    _volume_hints(lines, out, rows)
    assert out["2.7.24"]["status"] == "review"
    assert out["2.7.24"]["our_qty"] == round(184.48 * 70 / 1000, 4)
    assert "70" in out["2.7.24"]["reason"]
    assert out["2.7.58"]["status"] == "not_found"
