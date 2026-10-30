"""The floor schedule on 9335 MH.pdf is a ruled table, read with its units."""
from pathlib import Path

import pytest

from azboq.schedules.finishes import finish_areas, finish_kind, finish_sum
from azboq.schedules.layers import floor_rows, layer_lines, layer_measure, layers_of
from azboq.schedules.openings import opening_rows, openings_area, resolve_count, sills_area
from azboq.text.normalise import fold_key
from azboq.schedules.tables import read_pdf, split_room_run

PDF = Path(r"D:\AZ-BOQ\data\Hadrut DEPO\9335\9335 MH.pdf")


def test_room_run_splits_only_when_one_reading_fits():
    known = {str(n) for n in range(1, 30)}
    assert split_room_run("161819", known, 15) == ["16", "18", "19"]
    assert split_room_run("1213", known, 11) == ["12", "13"]
    # 1+2+3 and 1+23 both ascend, so the token is not split.
    assert split_room_run("123", {"1", "2", "3", "12", "23"}, None) is None


def _cells(tables, unit):
    out = []
    for table in tables:
        for row in table["rows"]:
            if row.get("section"):
                continue
            for cell in row["cells"]:
                if cell.get("unit") == unit:
                    out.append(cell["text"].replace(",", ".").replace(" ", ""))
    return " ".join(out)


def test_count_column_is_used_only_when_the_floors_add_up():
    assert resolve_count([29, 33, 62]) == 62
    assert resolve_count([9, 9]) == 9
    assert resolve_count([1, 5, 6]) == 6
    assert resolve_count([1, 2, 4]) is None


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_floor_schedule_areas_carry_square_metres():
    tables = read_pdf(PDF, pages=[20])
    blob = _cells(tables, "m²")
    for expected in ("1344", "43.8", "658.30", "129.0", "230.6", "538.4", "160", "35.40", "24.6"):
        assert expected in blob, blob


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_finish_and_window_schedules():
    tables = read_pdf(PDF, pages=[21])
    areas = _cells(tables, "m²")
    for expected in ("1368.7", "3380", "665.3", "686.7", "653.6", "96.0"):
        assert expected in areas, areas
    counts = _cells(tables, "each")
    assert "62" in counts and "29" in counts


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_window_opening_areas():
    rows = opening_rows(read_pdf(PDF, pages=[21]))
    glass = openings_area(rows, ["P-1", "P-2", "P-3", "P-4"], "sha", "9335 MH.pdf")
    pvc = openings_area(rows, ["P-5"], "sha", "9335 MH.pdf")
    doors = openings_area(rows, ["QP-1", "QP-2", "QP-3"], "sha", "9335 MH.pdf")
    assert glass.value == pytest.approx(252.276, abs=1e-6)
    assert pvc.value == pytest.approx(2.88, abs=1e-9)
    assert doors.value == pytest.approx(38.988, abs=1e-6)
    assert "P1_B_mm" in glass.inputs and glass.inputs["P1_n"].value == 62


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_window_sill_area_uses_the_printed_size():
    rows = opening_rows(read_pdf(PDF, pages=[21]))
    sills = {r["sill"]["mark"]: r for r in rows if r.get("sill")}
    assert set(sills) == {"Pa-1", "Pa-2", "Pa-3", "Pa-4", "Pa-5"}
    assert sills["Pa-2"]["sill"]["length_mm"] == 2000
    assert sills["Pa-2"]["sill"]["depth_mm"] == 400
    assert "2000x400" in sills["Pa-2"]["sill"]["text"].lower()
    got = sills_area(rows, "sha", "9335 MH.pdf")
    assert got.value == pytest.approx(37.52, abs=1e-9)


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_metal_door_area():
    rows = opening_rows(read_pdf(PDF, pages=[22]))
    metal = [r for r in rows if "metal" in fold_key(r.get("material") or "")]
    assert {r["mark"] for r in metal} == {"Q-1", "Q-9", "Q-9*"}
    assert all(not r["conflict"] for r in metal)
    got = openings_area(rows, [r["mark"] for r in metal], "sha", "9335 MH.pdf")
    assert got.value == pytest.approx(23.1, abs=1e-9)


def _door_marks(rows, material, limit, over=False):
    chosen = []
    for row in rows:
        if material not in fold_key(row.get("material") or "") or not row["B"] or not row["H"]:
            continue
        opening = row["B"] * row["H"] / 1_000_000
        if over:
            if opening > limit:
                chosen.append(row["mark"])
        elif opening <= limit:
            chosen.append(row["mark"])
    return chosen


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_door_rows_split_at_3_square_metres():
    rows = opening_rows(read_pdf(PDF, pages=[22]))
    pvc = _door_marks(rows, "pvc", 3)
    mdf = _door_marks(rows, "mdf", 3)
    wide = _door_marks(rows, "mdf", 3, over=True)
    assert pvc == ["Q-2", "Q-3", "Q-4"]
    assert mdf == ["Q-5", "Q-6", "Q-7"]
    assert wide == ["Q-8"]
    assert openings_area(rows, pvc, "sha", "9335 MH.pdf").value == pytest.approx(43.68, abs=1e-6)
    assert openings_area(rows, mdf, "sha", "9335 MH.pdf").value == pytest.approx(88.83, abs=1e-6)
    assert openings_area(rows, wide, "sha", "9335 MH.pdf").value == pytest.approx(6.72, abs=1e-6)


def test_finish_kind_reads_the_words_beside_the_area():
    assert finish_kind("ceiling", "Əhənglə ağardılır") == "whitewash"
    assert finish_kind("ceiling", "Hamarlanır,") == "paint"
    assert finish_kind("ceiling", "keyfiyyяtli емулсийа иля рянэлянир") == "paint"
    assert finish_kind("ceiling", "Метал каркас цзря metal асма таван") == "metal"
    assert finish_kind("ceiling", "Мetal karkas üzrя alçipan asma tavan, keyfiyyяtli emulsiya") == "plasterboard"
    assert finish_kind("wall", "Suvanır və əhənglə ağardılır") == "whitewash"
    assert finish_kind("wall", "Suvanыr vя") == "plaster"
    assert finish_kind("wall", "tavalarla цzlяnir") == "ceramic"


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_finish_schedule_sums():
    areas = finish_areas(read_pdf(PDF, pages=[21]))
    ceramic = [a["value"] for a in areas if a["kind"] == "ceramic"]
    assert sorted(ceramic) == [180.0, 190.0]

    def total(side, kind, floors=None):
        rule = {"id": kind, "side": side, "kind": kind, "unit": "m²", "floors": floors or []}
        return finish_sum(areas, rule, "sha", "9335 MH.pdf").value

    assert total("ceiling", "whitewash", ["basement"]) == pytest.approx(1368.7)
    assert total("ceiling", "paint") == pytest.approx(2005.6)
    assert total("ceiling", "plasterboard") == pytest.approx(96.0)
    assert total("ceiling", "metal") == pytest.approx(61.4)
    assert total("wall", "whitewash", ["basement"]) == pytest.approx(3380.0)
    assert total("wall", "plaster") == pytest.approx(3892.7)


def test_layer_text_keeps_the_thickness_and_drops_the_mesh_spacing():
    cement = layers_of(layer_lines("2.Beton döşənək qatı B10-100mm"))
    assert cement[0]["thickness_mm"] == 100
    mesh = layers_of(layer_lines("3.Bir qat torlu (Ø 4, ad -150x150mm,1m2 -1.35kq)- 40mm"))
    assert mesh[0]["thickness_mm"] == 40
    assert mesh[0]["kg_per_m2"] == 1.35
    joist = layers_of(layer_lines("Laqa taxta 100 X 50 (h) - 50 mm"))
    assert joist[0]["thickness_mm"] == 50
    text = '6.İstilik izolyasiya qatı-keramzit çınqılı-35 mm 5."150"markalı sement-qum məhlulu 1 qat torlu -30 mm'
    ker = [layer for layer in layers_of(layer_lines(text)) if "keramzit" in fold_key(layer["text"])]
    assert len(ker) == 1 and ker[0]["thickness_mm"] == 35


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_floor_layer_volumes_and_mesh_weights():
    rows = floor_rows(read_pdf(PDF, pages=[20]))
    spec = {"id": "keramzit", "floor": "basement", "type_no": "2", "material": "keramzit", "unit": "m³"}
    ker = layer_measure(rows, spec, "sha", "9335 MH.pdf")
    spec4 = {"id": "poly4", "floor": "floor_1", "type_no": "4", "material": "penopolist", "unit": "m³"}
    spec5 = {"id": "poly5", "floor": "floor_1", "type_no": "5", "material": "penopolist", "unit": "m³"}
    mesh4 = {"id": "mesh4", "floor": "floor_1", "type_no": "4", "material": "torlu", "unit": "t"}
    mesh5 = {"id": "mesh5", "floor": "floor_1", "type_no": "5", "material": "torlu", "unit": "t", "weight_from_type": "4"}
    assert ker.value == pytest.approx(1.533, abs=1e-9)
    assert layer_measure(rows, spec4, "sha", "9335 MH.pdf").value == pytest.approx(7.322, abs=1e-9)
    assert layer_measure(rows, spec5, "sha", "9335 MH.pdf").value == pytest.approx(13.174, abs=1e-9)
    assert layer_measure(rows, mesh4, "sha", "9335 MH.pdf").value == pytest.approx(0.14121, abs=1e-5)
    borrowed = layer_measure(rows, mesh5, "sha", "9335 MH.pdf")
    assert borrowed.value == pytest.approx(0.25407, abs=1e-5)
    assert "type 4" in borrowed.note


def test_a_decimal_schedule_area_counts_for_a_round_bill_quantity():
    from azboq.match.evidence import unit_carries
    assert unit_carries(39, {"schedule": True, "unit": "m²", "token": "39.00"}, "m²")
    assert not unit_carries(39, {"schedule": False, "unit": None, "token": "39"}, "m²")


def test_roof_window_count_ignores_the_mark_number():
    from azboq.match.evidence import Finder
    finder = Finder.__new__(Finder)
    finder.roof_windows = [
        {"building": "depot", "value": 9, "unit": "each", "context": "Dam pəncərəsi DP - 1 (9 əd)"},
        {"building": "heating_point", "value": 4, "unit": "each", "context": "Dam pəncərəsi DP-1 (4 əd.)"},
        {"building": "heating_point", "value": 2, "unit": "each", "context": "Dam pəncərəsi DP-1 (2 əd.)"},
    ]
    assert finder.roof_window("depot")["value"] == 9
    assert finder.roof_window("heating_point") is None


def test_gutter_and_downpipe_are_different_words():
    from azboq.match.evidence import subject_class
    assert subject_class("Novların düzəldilməsi: asma") == "gutter"
    assert subject_class("Novun ümumi uzunluğu L=190.5 p.m.") == "gutter"
    assert subject_class("Novalçaların ümumi uzunluğu L=154.2 p.m") == "downpipe"
    assert subject_class("Metal su axıdıcı sistemin qurulması") == "downpipe"
    assert subject_class("hər növbəti gediş") is None


def test_downpipe_note_does_not_add_up():
    from azboq.match.evidence import Finder
    finder = Finder.__new__(Finder)
    finder.by_value = {
        154.2: [{"building": "depot", "unit": "m", "value": 154.2,
                 "context": "Novalçaların ümumi uzunluğu L=154.2 p.m"}],
        5.4: [{"building": "depot", "unit": "m", "value": 5.4,
               "context": "Novalçalar Ø 100 mm; H=5.4 p.m - 5 ədəd"}],
        7.1: [{"building": "depot", "unit": "m", "value": 7.1,
               "context": "Novalçalar Ø 100 mm; H=7.1 p.m - 2 ədəd"}],
        7.9: [{"building": "depot", "unit": "m", "value": 7.9,
               "context": "Novalçalar Ø 100 mm; H=7.9 p.m - 3 ədəd"}],
        7.7: [{"building": "depot", "unit": "m", "value": 7.7,
               "context": "Novalçalar Ø 100 mm; H=7.7 p.m - 10 ədəd"}],
        8.1: [{"building": "depot", "unit": "m", "value": 8.1,
               "context": "Novalçalar Ø 100 mm; H=8.1 p.m - 6 ədəd"}],
    }
    got = finder.note_conflicts()
    assert got[0]["text"] == "downpipes: stated 154.2 m, itemised 190.5 m"


@pytest.mark.skipif(not PDF.exists(), reason="9335 MH.pdf is not on this machine")
def test_room_schedules_on_the_plans():
    from azboq.schedules.rooms import read_rooms
    found = {item["floor"]: item for item in read_rooms(PDF, pages=[4, 5, 6])}
    assert set(found) == {"basement", "floor_1", "floor_2"}
    garage = next(row for row in found["floor_1"]["rows"] if row["room"] == "1")
    assert garage["name"].startswith("Qaraj")
    assert garage["area"] == pytest.approx(658.30)
    assert found["floor_1"]["total"] == pytest.approx(1395.80)
    assert found["basement"]["total"] == pytest.approx(1360.80)
    assert found["floor_2"]["total"] == pytest.approx(779.00)
    assert found["floor_2"]["gap"] == 0
    assert found["basement"]["gap"] == pytest.approx(-11)
    assert found["floor_1"]["gap"] == pytest.approx(2.9)


def test_garage_room_is_printed_twice():
    from azboq.schedules.conflicts import same_room_conflicts
    from azboq.schedules.rooms import read_rooms
    conflicts = same_room_conflicts(read_pdf(PDF, pages=[20, 21]), read_rooms(PDF, pages=[5]))
    assert len(conflicts) == 1
    assert "658.30" in conflicts[0]["text"]
    assert "665.3" in conflicts[0]["text"]
    assert "Qaraj" in conflicts[0]["text"]
    assert "1st floor" in conflicts[0]["text"]


def test_a_nearby_schedule_figure_needs_the_same_words():
    from azboq.match.evidence import Finder
    finder = Finder.__new__(Finder)
    finder.schedule = [
        {"value": 1368.7, "unit": "m²", "building": "depot", "context": "tavan ehengle agardilir", "row_label": ""},
        {"value": 1344.0, "unit": "m²", "building": "depot", "context": "keramik doseme", "row_label": ""},
    ]
    assert finder.near_schedule(1414.2, "m²", "depot", "Dam örtüyünün sement qum məhlulu ilə hamarlanması") is None
    hit = finder.near_schedule(1333.6, "m²", "depot", "Zirzəmi tavanının əhənglə ağardılması")
    assert hit is not None and hit["value"] == 1368.7
