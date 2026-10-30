"""Real strings from the Hadrut package."""
from azboq.text.legacy import decode
from azboq.text.mtext import decode_mtext
from azboq.text.normalise import az_lower, az_upper, canonical_unit, fold_homoglyphs, fold_key, parse_number


def test_room_schedule_title_a3_arial():
    assert decode("ЙЕРЛЯШЭЯЛЯРИН ЕКСПЛИКАСИЙАСЫ", "A3ArialAzLatNormal").text == "YERLƏŞGƏLƏRİN EKSPLİKASİYASI"


def test_unit_header_generator_sheet():
    assert decode("Юлчц ващиди", "A3ArialAzLatNormal").text == "Ölçü vahidi"
    assert decode("ЭЮСТЯРИЪИЛЯРИ", "A3ArialAzLatNormal").text == "GÖSTƏRİCİLƏRİ"


def test_title_block_signature():
    assert decode("Имза вя тарих", "A3TimesAzLatNormal").text == "İmza və tarix"


def test_zh_differs_by_family():
    assert decode("эцжц", "ArialCyr").text == "gücü"


def test_russian_stays_russian_without_font():
    assert decode("ГОСТ 34028-2016").text == "ГОСТ 34028-2016"
    assert decode("РАЗМЕРЫ").text == "РАЗМЕРЫ"
    assert decode("ОСНОВАНИЯ ЗДАНИЙ И СООРУЖЕНИЙ").text == "ОСНОВАНИЯ ЗДАНИЙ И СООРУЖЕНИЙ"


def test_mixed_sentence_without_font():
    raw = "Лайищя комплексиндя Yanğın siqnalizasiya шябякяси нязярдя тутулуб."
    assert decode(raw).text == "Layihə kompleksində Yanğın siqnalizasiya şəbəkəsi nəzərdə tutulub."


def test_scheme_l_word_mixing_scripts():
    assert decode("Tяmizlik").text == "Təmizlik"


def test_mtext_font_switch_inside_number():
    raw = r"{\C0;8\fArial Narrow|b0|i0|c238|p34;3\fArial Narrow|b0|i0|c204|p34;.\fArial Narrow|b0|i0|c238|p34;10}"
    assert decode_mtext(raw).decoded == "83.10"


def test_mtext_font_switch_inside_word_and_percent_codes():
    assert decode_mtext(r"{\fArial Narrow|b0|i0|c238|p34;Kütl\fTimes New Roman|b0|i0|c238|p18;ə}").decoded == "Kütlə"
    assert decode_mtext(r"6{\fArial Narrow|b0|i0|c238|p34;%%C14 A500C}").decoded == "6Ø14 A500C"
    assert decode_mtext(r"Sütun\PS -1").decoded == "Sütun\nS -1"


def test_mixed_script_word_is_one_azeri_word():
    from azboq.text.legacy import fold_mixed_words
    assert fold_mixed_words("Haмarlayıcı seмenт-quм мəhlulu - 27 мм") == "Hamarlayıcı sement-qum məhlulu - 27 mm"
    assert fold_mixed_words("ГОСТ 5781-82*") == "ГОСТ 5781-82*"
    assert fold_mixed_words("А500C") == "A500C"


def test_homoglyphs_folded_only_in_codes():
    assert fold_homoglyphs("А500C") == "A500C"
    assert fold_homoglyphs("Ø8 А240C L=1760") == "Ø8 A240C L=1760"
    assert fold_homoglyphs("Мtv-1") == "Mtv-1"
    assert fold_homoglyphs("ГОСТ 34028-2016") == "ГОСТ 34028-2016"


def test_azerbaijani_case():
    assert az_upper("istirahət") == "İSTİRAHƏT"
    assert az_lower("İŞIQ") == "işıq"
    assert fold_key("Şaquli planlaşdırma") == "saquli planlasdirma"


def test_units_and_numbers():
    assert canonical_unit("m(3)") == ("m³", True)
    assert canonical_unit("pagon metr") == ("m", True)
    assert canonical_unit("FF") == ("FF", False)
    assert parse_number("383,7") == 383.7
    assert parse_number("1 395.80") == 1395.8
