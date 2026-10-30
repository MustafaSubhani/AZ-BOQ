"""A crop uses the image's own scale. Y on a drawing points up; a page image does not."""
import pytest

from azboq.crops import dxf_to_px, pdf_to_px, region_transform


def test_a_pdf_point_lands_on_the_110_dpi_image():
    assert pdf_to_px([72, 144, 216, 288]) == pytest.approx([110, 220, 330, 440])


def test_a_drawing_point_flips_y_and_keeps_a_letterbox_offset():
    # Top-left of the drawing is the top-left pixel when the tile matches the box.
    assert dxf_to_px([0, 10], [0, 0, 10, 10], 100, 100) == pytest.approx([0, 0])
    assert dxf_to_px([10, 0], [0, 0, 10, 10], 100, 100) == pytest.approx([100, 100])
    # A wide tile leaves an equal margin on the left and the right.
    assert dxf_to_px([0, 10], [0, 0, 10, 10], 200, 100) == pytest.approx([50, 0])
    transform = region_transform([0, 0, 10, 10], 200, 100)
    assert transform["scale"] == pytest.approx(10)
    assert transform["offset"] == pytest.approx([50, 0])
