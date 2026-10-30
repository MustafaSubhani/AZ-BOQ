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
