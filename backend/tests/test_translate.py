from azboq.text.translate import check, glossary_translate, protected_tokens


def test_numbers_and_codes_must_survive():
    src = "Çalovunun tutumu 0,5 m3 olan ekskavatorlarla, A500C, 17 t"
    assert check(src, "Excavators with 0.5 m3 bucket, A500C, 17 t")["numbers_ok"]
    assert not check(src, "Excavators with 0.6 m3 bucket, A500C, 17 t")["numbers_ok"]
    assert "0.5" in protected_tokens(src) and "A500C" in protected_tokens(src)


def test_glossary_translates_structured_section_titles():
    assert glossary_translate("4 çıxışlı Yanğın Deposu binası  (Torpaq işləri)") == "4-bay fire station building (Earthworks)"
    assert glossary_translate("Nəzarətçi otağı (Dam örtüyü)") == "Guard room (Roof covering)"


def test_glossary_refuses_partial_cover():
    assert glossary_translate("Çalovunun tutumu 0,5 m3 olan ekskavatorlarla qruntun qazılması") is None
