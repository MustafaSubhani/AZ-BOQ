"""Overall dimensions are taken from a plan, not from a facade or a section."""
import pytest

from azboq.engine.extract import _is_plan


def test_a_later_numbered_file_is_not_the_same_drawing():
    from azboq.engine.locate import _name_has
    assert _name_has("yangin su anbari dk", r"9335 Xocavend yangin su anbari dk son.dwg")
    assert not _name_has("yangin su anbari dk", r"9335 Xocavend yangin su anbari dk 2.dwg")
    assert _name_has("(SON)", r"YRS - VN -9335 hadrut xocevend (SON).dwg")


def test_excel_is_stopped_when_it_hangs():
    import time
    from azboq.export.client_bill import run_bounded
    killed = []

    def work(box):
        box["pid"] = 4242
        time.sleep(2)

    with pytest.raises(TimeoutError):
        run_bounded(work, 0.05, killed.append)
    assert killed == [4242]
    assert _is_plan({"title": "1-ci mərtəbənin planı"})
    assert _is_plan({"title": "Damın planı"})
    assert _is_plan({"title": "Texniki zirzəmidə plan ."})
    assert not _is_plan({"title": "Fasad 1-10"})
    assert not _is_plan({"title": "Kəsim 1-1"})
    assert not _is_plan({"title": "Baş plan"})
    assert not _is_plan({"title": "Şaquli planlaşdırma"})
    assert not _is_plan({"title": "YERLƏŞGƏLƏRİN EKSPLİKASİYASI"})
    assert not _is_plan(None)


def test_a_long_note_keeps_the_sentence_around_the_number():
    from azboq.index.numbers import entries_from_text
    text = ("x" * 300) + " L=45200 mm " + ("y" * 300)
    found = entries_from_text(text, {})
    ctx = next(e["context"] for e in found if e["value"] == 45200)
    assert "45200" in ctx
    assert len(ctx) < 260
    assert 80 < ctx.index("45200") < 140


def test_a_level_mark_is_not_a_quantity_hit():
    from azboq.match.evidence import _beside_level
    assert _beside_level({"token": "2.700", "context": "örtük səviyyəsində -2.700"})
    assert _beside_level({"token": "±2.700", "context": "±2.700"})
    assert not _beside_level({"token": "45200", "context": "plan 45200"})


def test_planlasdirma_is_not_chosen_as_the_sheet_title():
    from azboq.sheets import region_title
    title = region_title(
        [{"text": "Şaquli planlaşdırma", "h": 12}, {"text": "1-ci mərtəbənin planı", "h": 5}],
        "stamp",
    )
    assert title.startswith("1-ci")
    from azboq.engine.extract import _pdf_confirms
    assert _pdf_confirms({"id": "x", "building": "tower", "unit": "m"}, 45200) == []
