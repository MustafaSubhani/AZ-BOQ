"""Hatch links, steel families, and a review that sets one input."""
import pytest
from shapely.geometry import Polygon

from azboq.areas import link_hatches_to_rooms
from azboq.dwg.read import outlines_of
from azboq.reviews import apply_reviews


def test_one_room_tag_links_the_hatch_and_two_tags_do_not_pick():
    hatch = {"handle": "H", "outline": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]], "holes": [], "area_du2": 100}
    rooms = {"1": {"room": "1", "label": "1 Qaraj", "name": "Qaraj"}}
    one = link_hatches_to_rooms([hatch], [{"text": "1", "at": [5, 5]}, {"text": "9", "at": [30, 30]}], rooms)
    assert one["H"]["kind"] == "room"
    assert one["H"]["label"] == "1 Qaraj"
    two = link_hatches_to_rooms([hatch], [{"text": "1", "at": [3, 3]}, {"text": "2", "at": [7, 7]}], rooms)
    assert two["H"]["kind"] == "area_conflict"


def test_a_hatch_outline_keeps_the_outer_ring():
    rings, holes = outlines_of(Polygon([(0, 0), (1000, 0), (1000, 500), (0, 500)]), 1)
    assert rings and rings[0][0] == [0, 0]
    assert holes == []


def test_set_input_recomputes_the_formula_and_leaves_the_original():
    takeoff = {"items": [{"id": "glass", "value": {
        "value": 3, "unit": "m²", "method": "derived", "status": "extracted", "formula": "width * height / 1000000",
        "inputs": {"width": {"value": 1000, "unit": "mm"}, "height": {"value": 1000, "unit": "mm"}},
        "sources": [], "searched": [], "rejected": [], "conflicts": [], "missing": [], "note": "",
    }}]}
    reviewed = apply_reviews(takeoff, [{
        "id": 9, "action": "set_input", "target_kind": "item", "target_id": "glass",
        "payload": {"name": "height", "value": 2000, "unit": "mm"}, "reason": "the schedule says 2000", "author": "Ada",
    }])
    assert reviewed["items"][0]["value"]["value"] == pytest.approx(2)
    assert takeoff["items"][0]["value"]["value"] == 3
