"""Copies of one sheet are one sheet, and a plot of it is not a second fact."""
from azboq.dwg.crosscheck import reading_status
from azboq.engine.extract import _source_affected
from azboq.sheets import assign_families
from azboq.values import Source


def test_the_9335_copy_is_the_one_that_is_read():
    regions = [
        {"id": "R10", "title": "Damın planı", "number": {"order": "9336", "mark": "02", "discipline_mark": "MH"}},
        {"id": "R11", "title": "Damın planı", "number": {"order": "9337", "mark": "02", "discipline_mark": "MH"}},
        {"id": "R12", "title": "Damın planı", "number": {"order": "9335", "mark": "02", "discipline_mark": "MH"}},
        {"id": "R35", "title": "Another sheet", "number": {"order": "9183", "mark": "6", "discipline_mark": "YS"}},
    ]
    assign_families(regions)
    by_id = {r["id"]: r for r in regions}
    assert by_id["R12"].get("copy_of") is None
    assert by_id["R10"]["copy_of"] == "R12" and by_id["R11"]["copy_of"] == "R12"
    assert by_id["R35"]["only_other_order"] is True
    assert by_id["R35"].get("copy_of") is None
    both = [
        {"id": "R27", "title": "Dam", "number": {"order": "9335", "mark": "04", "discipline_mark": "MT"}},
        {"id": "R28", "title": "Dam", "number": {"order": "9335", "mark": "04", "discipline_mark": "MT"}},
    ]
    assign_families(both)
    assert both[0].get("copy_of") is None and both[1].get("copy_of") is None


def test_a_region_disagreement_does_not_touch_text():
    cross = {"type_diffs": [{"type": "REGION", "oda": 30, "libredwg": 0}], "layer_diffs": [{"layer": "polygon"}]}
    text = Source("a", "f.dwg", {"kind": "dxf_entity", "layer": "ramka"})
    dim = Source("a", "f.dwg", {"kind": "dxf_dimension", "layer": "0"})
    on_polygon = Source("a", "f.dwg", {"kind": "dxf_entity", "layer": "polygon"})
    assert _source_affected(text, cross) is False
    assert _source_affected(dim, cross) is False
    assert _source_affected(on_polygon, cross) is True


def test_a_failed_second_reader_is_not_a_disagreement():
    assert reading_status("converted", {"libredwg_status": "crash", "libredwg_total": 0, "agree": False}) == "single reader"
    assert reading_status("converted", {"libredwg_status": "ok", "libredwg_total": 0, "agree": False}) == "single reader"
    assert reading_status("converted", {"libredwg_status": "ok", "libredwg_total": 10, "agree": False}) == "reader disagreement"
    assert reading_status("converted", {"libredwg_status": "ok", "libredwg_total": 10, "agree": True}) == "read"
