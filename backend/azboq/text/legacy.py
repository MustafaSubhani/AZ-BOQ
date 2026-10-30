"""Decode text written in legacy Azerbaijani fonts that draw Latin letters at Cyrillic code points.

Decoding is chosen per run by its font. When the font is unknown, a word is decoded
only if it is Cyrillic and reads better as Azerbaijani than as Russian. Genuine
Russian (ГОСТ, РАЗМЕРЫ, норм titles) stays Russian. Raw text is always kept.
"""
import json
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from .. import config
from .normalise import az_lower, az_upper, fold_key

_CYR = re.compile(r"[\u0400-\u04FF]")
_WORD = re.compile(r"[\w\u0400-\u04FF'’]+")
_MIXED_WORD = re.compile(r"[\wƏəÖöÜüÇçŞşĞğİı\u0400-\u04FF]+")
_LATIN = re.compile(r"[A-Za-zƏəÖöÜüÇçŞşĞğİı]")
_CYR_UNIT = {"мм": "mm", "ММ": "mm", "м²": "m²", "м³": "m³", "м2": "m2", "м3": "m3"}

DEFAULT_FAMILY = "A3ArialAzLatNormal"

FONT_FAMILY_PATTERNS = [
    (r"(?i)a3ti\(la\)|a3[ _]?times[ _]?az[ _]?lat|a3timesazlat", "A3TimesAzLatNormal"),
    (r"(?i)a2ti\(la\)|a2[ _]?times", "A2TimesAzLatNormal"),
    (r"(?i)a3[ _]?arial[ _]?az[ _]?cyr", "A3ArialAzCyrNormal"),
    (r"(?i)a3[ _]?arial", "A3ArialAzLatNormal"),
    (r"(?i)arial[ _]?azeri[ _]?lat", "ArialAzeriLat"),
    (r"(?i)arial[ _]?az[ _]?lat", "ArialAzLat"),
    (r"(?i)arial[ _]?cyr", "ArialCyr"),
    (r"(?i)azlat|azcyr|azeri", DEFAULT_FAMILY),
]

RUSSIAN_WORDS = {
    "гост", "снип", "размеры", "размер", "размер2", "стены", "стена", "двери", "окна", "оси", "ось", "мебель",
    "невидимка", "перегородка", "колонна", "колонны", "лист", "примечание", "ном", "пера", "общий", "чертеж",
    "элемент", "модели", "зона", "оболочка", "крыша", "конструктив", "ограждающий", "интерьер", "аннотация",
    "текст", "поверхность", "умывальник", "унитаз", "ворота", "гаражные", "подъемные", "символ", "поддона",
    "душа", "линия", "связь", "автоматика", "соедин", "соединение", "газа", "розетки", "выкл", "схема", "шкаф",
    "надписи", "спот", "свет", "формат", "сгенерир", "стиль", "копия", "лист1", "и", "в", "на", "для", "по",
    "типа", "тип", "кабель", "провод", "длина", "ширина", "высота", "масса", "вес", "итого", "всего",
}


@dataclass
class Decoded:
    text: str
    scheme: str          # "unicode", "font_table", "word_heuristic", "mixed"
    confidence: float    # 0..1
    changed: int
    undecoded: int


@lru_cache(maxsize=None)
def _tables() -> dict:
    tables = {}
    if config.LEGACY_FONT_DIR.exists():
        for p in config.LEGACY_FONT_DIR.glob("*.json"):
            tables[p.stem] = {slot: row["to"] for slot, row in json.loads(p.read_text(encoding="utf-8")).items()}
    overrides = config.RULES_DIR / "legacy_font_overrides.yaml"
    if overrides.exists():
        for row in yaml.safe_load(overrides.read_text(encoding="utf-8")) or []:
            if "alias_of" in row:
                tables[row["family"]] = dict(tables.get(row["alias_of"], {}))
            else:
                tables.setdefault(row["family"], {})[row["slot"]] = row["value"]
    return tables


def family_for_font(font: str | None) -> str | None:
    if not font:
        return None
    for pattern, fam in FONT_FAMILY_PATTERNS:
        if re.search(pattern, font):
            return fam
    return None


@lru_cache(maxsize=None)
def _table(family: str) -> dict:
    t = _tables()
    table = dict(t.get(DEFAULT_FAMILY, {}))
    table.update(t.get(family, {}))
    # A slot seen only in one case gets its partner: ш→ş implies Ш→Ş.
    for slot, to in list(table.items()):
        partner = slot.upper() if slot.islower() else slot.lower()
        if partner != slot and partner not in table:
            table[partner] = (az_upper(to) if slot.islower() else az_lower(to))
    return table


def fold_mixed_words(text: str) -> str:
    """A word that mixes scripts is one word drawn with two fonts: 'seмenт' is 'sement'."""
    def fix(m):
        w = m.group(0)
        if w in _CYR_UNIT:
            return _CYR_UNIT[w]
        if _CYR.search(w) and _LATIN.search(w):
            return decode_with_family(w, DEFAULT_FAMILY).text
        return w
    return _MIXED_WORD.sub(fix, text)


def decode_with_family(text: str, family: str) -> Decoded:
    table = _table(family)
    out, changed, undecoded = [], 0, 0
    for ch in text:
        if _CYR.match(ch):
            to = table.get(ch)
            if to is None:
                undecoded += 1
                out.append(ch)
            else:
                changed += to != ch
                out.append(to)
        else:
            out.append(ch)
    total = changed + undecoded
    conf = 1.0 if total == 0 else changed / total
    return Decoded("".join(out), "font_table", round(conf, 3), changed, undecoded)


@lru_cache(maxsize=1)
def az_vocabulary() -> frozenset:
    """Azerbaijani words seen in Unicode text: the bill descriptions plus drawing text already in Latin."""
    words = set()
    p = config.CACHE_DIR / "az_vocab.json"
    if p.exists():
        words.update(json.loads(p.read_text(encoding="utf-8")))
    return frozenset(words)


def _russian_score(word: str) -> float:
    w = word.lower()
    s = 3.0 if w in RUSSIAN_WORDS else 0.0
    s += 1.0 * sum(w.count(c) for c in "ьё")
    s += 1.5 if re.search(r"(ть|ие|ия|ий|ых|ый|ой|ая|ое|ые|ую|ов|ей|ям|ам|ах|ция|ние|ний|ния|ании|ений)$", w) else 0.0
    s += 1.0 if re.search(r"(жд|щи|чт|ств|зд|ьн)", w) else 0.0
    return s


def _az_score(word: str, decoded: str) -> float:
    w = word.lower()
    s = 3.0 if fold_key(decoded) in az_vocabulary() else 0.0
    s += 1.2 * sum(w.count(c) for c in "яцщэъ")
    s += 0.6 * sum(w.count(c) for c in "юг")
    return s


def decode_unknown(text: str) -> Decoded:
    """No font information: judge the sentence, then decide word by word.

    If the Cyrillic words of a string lean Azerbaijani overall and none is clearly
    Russian, all of them are decoded (neutral words like тутулуб follow their
    neighbours). Otherwise each word is decided on its own scores.
    """
    if not _CYR.search(text):
        return Decoded(text, "unicode", 1.0, 0, 0)
    words = [(m, m.group(0)) for m in _WORD.finditer(text)]
    scored = []
    for m, word in words:
        if not _CYR.search(word):
            scored.append((m, word, None))
            continue
        cand = decode_with_family(word, DEFAULT_FAMILY)
        mixed = bool(re.search(r"[A-Za-zəöüçşğıİ]", word))
        az, ru = _az_score(word, cand.text), _russian_score(word)
        scored.append((m, word, (cand, mixed, az, ru)))
    judged = [s for s in scored if s[2] is not None]
    total_az = sum(s[2][2] for s in judged)
    total_ru = sum(s[2][3] for s in judged)
    clearly_russian = any(s[2][3] >= 3.0 and s[2][2] < 3.0 for s in judged)
    sentence_az = total_az > total_ru and not clearly_russian
    pieces, last, changed, undecoded = [], 0, 0, 0
    for m, word, info in scored:
        pieces.append(text[last:m.start()])
        last = m.end()
        if info is None:
            pieces.append(word)
            continue
        cand, mixed, az, ru = info
        if mixed or sentence_az or az > ru:
            pieces.append(cand.text)
            changed += cand.changed
            undecoded += cand.undecoded
        else:
            pieces.append(word)
    pieces.append(text[last:])
    conf = 0.6 if judged else 1.0
    return Decoded("".join(pieces), "word_heuristic", conf, changed, undecoded)


def decode(text: str, font: str | None = None) -> Decoded:
    """Decode one run. A legacy font decides; otherwise fall back to the word heuristic."""
    if not text or not _CYR.search(text):
        return Decoded(text or "", "unicode", 1.0, 0, 0)
    fam = family_for_font(font)
    if fam:
        return decode_with_family(text, fam)
    return decode_unknown(text)
