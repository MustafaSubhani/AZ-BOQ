"""A review is a stored decision. Its arithmetic is not Python."""
import pytest

from azboq.reviews import ExprError, add_review, apply_reviews, evaluate, manual_value, supersede


def test_the_expression_parser_does_not_run_python():
    assert evaluate("2 + 3 * 4") == 14
    assert evaluate("2*(3+4)") == 14
    assert evaluate("-3 + 5") == 2
    assert evaluate("1200 × 2700 × 62 ÷ 1000000") == pytest.approx(200.88)
    assert evaluate("sum(1, 2, 3)") == 6
    assert evaluate("round(1.26, 1)") == pytest.approx(1.3)
    assert evaluate("P1_B_mm * 2", {"P1_B_mm": 1200}) == 2400
    with pytest.raises(ExprError):
        evaluate("__import__('os')")
    with pytest.raises(ExprError):
        evaluate("unknown")
    with pytest.raises(ExprError):
        evaluate("1 / 0")


def test_an_override_replaces_the_item_and_a_reset_removes_it(tmp_path):
    db = tmp_path / "reviews.sqlite"
    takeoff = {"items": [{"id": "glass", "unit": "m²", "building": "depot",
                          "value": {"value": 252.276, "unit": "m²", "method": "derived", "status": "extracted",
                                    "sources": [{"file_id": "f", "file_name": "a.pdf", "locator": {}}],
                                    "formula": None, "inputs": {}, "searched": [], "rejected": [],
                                    "conflicts": [], "missing": [], "note": ""}}]}
    with pytest.raises(ExprError):
        add_review("item", "glass", "override", {"expression": "250", "unit": "m²"}, "  ", "Ada", db)
    review_id = add_review("item", "glass", "override",
                           {"expression": "250", "unit": "m²", "variables": {}}, "counted again", "Ada", db)
    reviewed = apply_reviews(takeoff, db=db)
    assert reviewed["review_ids"] == [review_id]
    assert reviewed["items"][0]["value"]["value"] == 250
    assert reviewed["items"][0]["value"]["method"] == "manual"
    assert reviewed["items"][0]["value"]["note"] == "Ada: counted again"
    assert takeoff["items"][0]["value"]["value"] == 252.276
    supersede(review_id, "Ada", "the engine value stands", db)
    assert apply_reviews(takeoff, db=db)["items"][0]["value"]["value"] == 252.276


def test_a_line_override_replaces_only_that_measured_quantity():
    from azboq.match.run import _apply_overrides

    lines = [{"id": "L1", "qty": 10.5}, {"id": "L2", "qty": 4}]
    out = {
        "L1": {"status": "different", "our_qty": 12.0, "reason": "the schedule prints 12"},
        "L2": {"status": "review", "our_qty": None, "reason": "only weak candidates"},
    }
    reviews = [
        {"id": 7, "action": "override", "target_kind": "line", "target_id": "L1",
         "payload": {"expression": "10,5"}, "author": "Ada", "reason": "counted the hatch"},
        {"id": 8, "action": "decide", "target_kind": "line", "target_id": "L2",
         "payload": {"value": 4}, "author": "Ada", "reason": "not an override"},
        {"id": 9, "action": "override", "target_kind": "line", "target_id": "L2",
         "payload": {"expression": "3 x 2"}, "author": "Ada", "reason": "two bays"},
    ]
    _apply_overrides(lines, out, reviews)
    assert out["L1"]["our_qty"] == 10.5
    assert out["L1"]["status"] == "matched"
    assert out["L1"]["engine_qty"] == 12.0
    assert out["L1"]["engine_reason"] == "the schedule prints 12"
    assert out["L1"]["override"]["expression"] == "10.5"
    assert out["L1"]["gap"] is None
    assert out["L2"]["our_qty"] == 6
    assert out["L2"]["status"] == "different"
    assert out["L2"]["gap"] == pytest.approx(-2)
    assert "Ada set this to 6" in out["L2"]["reason"]


def test_a_line_override_has_to_be_a_real_sum(tmp_path, monkeypatch):
    import azboq.config as config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "reviews.sqlite")
    with pytest.raises(ExprError):
        add_review("line", "L1", "override", {"expression": "nope"}, "because", "Ada")
    with pytest.raises(ExprError):
        add_review("line", "L1", "override", {"expression": "1/0"}, "because", "Ada")
    assert add_review("line", "L1", "override", {"expression": "3 x 2,5"}, "two and a half", "Ada")


def test_a_bad_line_override_leaves_the_engine_figure():
    from azboq.match.run import _apply_overrides

    out = {"L1": {"status": "different", "our_qty": 12.0, "reason": "the schedule prints 12"}}
    _apply_overrides(
        [{"id": "L1", "qty": 10}],
        out,
        [{"id": 1, "action": "override", "target_kind": "line", "target_id": "L1",
          "payload": {"expression": "nope"}, "author": "Ada", "reason": "bad"}],
    )
    assert out["L1"]["our_qty"] == 12.0
    assert "override" not in out["L1"]


def test_removing_a_line_override_restores_the_engine_figure(tmp_path, monkeypatch):
    import azboq.config as config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "reviews.sqlite")
    from azboq.match.run import _apply_overrides

    review_id = add_review("line", "L1", "override", {"expression": "9"}, "short count", "Ada")
    out = {"L1": {"status": "matched", "our_qty": 10.0, "reason": "printed"}}
    _apply_overrides([{"id": "L1", "qty": 10}], out)
    assert out["L1"]["our_qty"] == 9
    assert out["L1"]["status"] == "different"
    supersede(review_id, "Ada", "the engine figure stands")
    restored = {"L1": {"status": "matched", "our_qty": 10.0, "reason": "printed"}}
    _apply_overrides([{"id": "L1", "qty": 10}], restored)
    assert restored["L1"]["our_qty"] == 10.0
    assert "override" not in restored["L1"]


def test_manual_value_names_its_inputs():
    value = manual_value(
        {"expression": "width * height / 1000000", "unit": "m²",
         "variables": {"width": 1200, "height": 2700}, "units": {"width": "mm", "height": "mm"}},
        "from the schedule", "Ada", 4,
    )
    assert value.value == pytest.approx(3.24)
    assert value.formula == "width * height / 1000000"
    assert value.inputs["width"].value == 1200
    assert "Ada: from the schedule" == value.note
