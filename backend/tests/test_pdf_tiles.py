import pymupdf
import pytest

from azboq import config
from azboq.pdf import tiles


@pytest.fixture
def package(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "TILES_DIR", tmp_path / "tiles")
    config.DATA_DIR.mkdir()
    config.TILES_DIR.mkdir()
    doc = pymupdf.open()
    doc.new_page(width=720, height=360)
    doc.save(config.DATA_DIR / "sheet.pdf")
    return {"sha256": "a" * 64, "rel": "sheet.pdf"}


def test_page_is_drawn_at_the_viewer_scale(package):
    out = tiles.page_tile(package, 0)
    pix = pymupdf.Pixmap(str(out))
    assert (pix.width, pix.height) == (1100, 550)


def test_stored_page_needs_no_source(package):
    tiles.page_tile(package, 0)
    (config.DATA_DIR / "sheet.pdf").unlink()
    assert tiles.page_tile(package, 0).exists()


def test_missing_source_is_an_error(package):
    (config.DATA_DIR / "sheet.pdf").unlink()
    with pytest.raises(FileNotFoundError):
        tiles.page_tile(package, 0)


def test_render_all_reports_a_missing_source(package):
    (config.DATA_DIR / "sheet.pdf").unlink()
    res = tiles.render_all({"files": [package]})
    assert res["pages"] == 0 and res["failed"][0]["file"] == "sheet.pdf"
