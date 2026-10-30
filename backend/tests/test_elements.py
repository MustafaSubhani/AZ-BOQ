"""Bill descriptions name an element. The ceramic wall areas stay a candidate."""
import pytest

from azboq import store
from azboq.match.elements import classify


def test_a_stated_area_and_thickness_explain_the_line():
    from azboq.match.stated import stated_quantity
    stated = stated_quantity("Daxili kərpic divar hörgüsü (1201,7 m², qal=20 sm)")
    assert stated["qty"] == 1201.7
    assert stated["unit"] == "m²"
    assert stated["thickness_m"] == 0.2
    assert stated_quantity("pəncərə bloklarının quraşdırılması (252,28 m²)")["qty"] == 252.28
    assert stated_quantity("çalovu 0,5 (0,5-0,63) m3") is None
    assert stated_quantity("boru D57x3.5mm") is None


def test_element_words():
    assert classify("pəncərəaltı mərmər") == "sill"
    assert classify("su axıdıcı boru") == "downpipe"
    assert classify("novalça") == "downpipe"
    assert classify("yağış nov") == "gutter"
    assert classify("növbəti gediş") is None
    assert classify("pəncərə şüşəsi") == "window"
    assert classify("metal qapı") == "door"
    assert classify("armatur məftil") == "mesh"
    assert classify("döşənək armaturlanması") == "mesh"
    assert classify("penopolistirol") == "polystyrene"
    assert classify("keramoqranit") == "porcelain"
    assert classify("laminat") == "laminate"
    assert classify("mozaik döşəmə") == "terrazzo"
    assert classify("divar keramik") == "wall_tiles"
    assert classify("divarların suvanması") == "wall_plaster"
    assert classify("zirzəmi tavan") == "ceiling"
    assert classify("Divarların üzlənməsi") is None


needs_bill = pytest.mark.skipif(store.get("bill") is None, reason="bill has not been read")


def test_tile_facing_stays_a_candidate():
    from azboq.match.run import _tile_candidate
    line = {"description": "divar tavalarla üzlənməsi", "unit": "m²", "building": "depot", "qty": 474.2}
    areas = [
        {"value": 190.0, "building": "depot", "floor": "floor_1", "page": 21, "file_id": "abc",
         "file_name": "9335 MH.pdf", "description": "keramik", "cell": {"text": "190.0", "bbox": [1, 2, 3, 4]}},
        {"value": 180.0, "building": "depot", "floor": "floor_2", "page": 21, "file_id": "abc",
         "file_name": "9335 MH.pdf", "description": "keramik", "cell": {"text": "180.0", "bbox": [5, 6, 7, 8]}},
    ]
    hit = _tile_candidate(line, areas)
    assert hit["status"] == "review"
    assert hit["our_qty"] is None
    assert "190 + 180 = 370" in hit["reason"]
    assert _tile_candidate({**line, "building": "tower"}, areas) is None
    assert _tile_candidate({**line, "description": "divarların suvanması"}, areas) is None


@needs_bill
def test_simple_plaster_is_not_the_tile_line():
    bill = {line["id"]: line for line in store.get("bill")["lines"]}
    assert classify(bill["2.8.11"]["description"]) == "wall_plaster"
    assert classify(bill["2.8.12"]["description"]) == "wall_tiles"
    assert classify(bill["2.8.1"]["description"]) == "ceiling"
