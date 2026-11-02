"""A length stays on the sentence and the file that actually state it."""
from azboq.match.evidence import file_problem, length_problem, owning_clause, piece_total, subject_class


def test_other_order_and_second_variant_are_not_this_project():
    assert "9337" in file_problem({"sheet": "9337- 1- RS", "file": "a.dwg"})
    assert file_problem({"sheet": "9335 -1- SK", "file": "9335-1-SK Xocavənd depo.dwg"}) is None
    assert "variant" in file_problem({"sheet": "9335 -1- SK", "file": "9335-1-SK Xocavənd depo 2-ci variant.dwg"})


def test_a_gutter_sentence_does_not_confirm_a_pipe():
    entry = {"token": "190.5", "value": 190.5, "unit": "m",
             "context": "- Novun ümumi uzunluğu L=190.5 p.m."}
    assert subject_class(owning_clause(entry)) == "gutter"
    assert length_problem(entry, "Polietilen boru D110") == "the sentence names a different thing"
    assert length_problem(entry, "Novların düzəldilməsi") is None


def test_the_clause_with_the_number_decides():
    entry = {"token": "12.8", "value": 12.8, "unit": "m",
             "context": "nov və novalça borularından istifadə olunmalıdır (PVC) -novun ümumi uzunlugu L= 12.8 p.m  -novalça boruları L= 3.3 p.m"}
    assert subject_class(owning_clause(entry)) == "gutter"


def test_two_pieces_are_the_length():
    entry = {"token": "16.3", "value": 16.3, "unit": "m",
             "context": "Novalçalar Ø 100 mm, h=16.3 p.m. - 2 əd"}
    assert piece_total(entry) == (32.6, 2)


def test_cyrillic_novalca_is_a_downpipe():
    assert subject_class("Новалчалар Ø 100 mm, h=16.3 p.m.") == "downpipe"


def test_a_unit_without_the_row_is_not_this_conduit():
    entry = {"token": "2510", "value": 2510.0, "unit": "m", "context": "2510 m", "row_label": ""}
    assert length_problem(entry, "Naqil üçün Qırçınlı PLASTİK yanmaz Boru (d= 25mm)")
    cable = {"token": "2140", "value": 2140.0, "unit": "m", "context": "2140 m", "row_label": "22 en kəsiyi 3x4mm²"}
    assert length_problem(cable, "0,6/1,0 kV-luq güc kabeli 3х4") is None


def test_a_road_area_sentence_does_not_confirm_a_thickness_line():
    from azboq.match.evidence import named_area_problem
    entry = {"token": "216.0", "value": 216.0, "unit": "m²",
             "context": "Yolların sahəsi - 216.0m²", "row_label": ""}
    assert named_area_problem(entry, "Qatın qalınlığı hər 1 sm dəyişdikdə (əlavə 3 sm)")
    assert named_area_problem(entry, "Yolların sahəsi") is None


def test_the_mark_moves_to_the_line_that_states_the_number():
    from azboq.engine.locate import focus_at
    entity = {"text": "2. leveling S=1620.70\n3. 3482.3 x 0.15 = 522.0 m3",
              "at": [0, 100], "h": 10, "attach": 1, "width": 400, "rot": 0}
    point = focus_at(entity, "522.0")
    assert point is not None
    assert point[1] < 90


def test_a_bare_number_is_not_a_length():
    entry = {"token": "13.20", "value": 13.2, "unit": None, "context": "metal 13.20"}
    assert length_problem(entry, "Məhəccər tutacaqsız") == "the number has no unit and only one nearby word"
