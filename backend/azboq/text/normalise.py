"""Azerbaijani-aware case, folding keys, units and numbers. Display text is never folded."""
import re
import unicodedata

_LOWER = str.maketrans({"İ": "i", "I": "ı"})
_UPPER = str.maketrans({"i": "İ", "ı": "I"})
_FOLD = str.maketrans({"ə": "e", "ı": "i", "ö": "o", "ü": "u", "ş": "s", "ç": "c", "ğ": "g", "ä": "ə"})

# Cyrillic letters that look exactly like Latin ones. Folded only inside code-like tokens.
HOMOGLYPHS = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i",
})
_CYR = re.compile(r"[\u0400-\u04FF]")
_LAT = re.compile(r"[A-Za-zƏəÖöÜüÇçŞşĞğİı]")
_CODE_TOKEN = re.compile(r"[\w\-./]+")


def az_lower(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(_LOWER).lower()


def az_upper(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(_UPPER).upper()


def match_key(s: str) -> str:
    """Lowercase with Azerbaijani rules, ä read as ə, whitespace collapsed."""
    s = az_lower(s).replace("ä", "ə")
    return re.sub(r"\s+", " ", s).strip()


def fold_key(s: str) -> str:
    """Accent-insensitive search key: ə→e, ı→i, ö→o and so on."""
    return match_key(s).translate(_FOLD).translate(_FOLD)


def is_code_like(token: str) -> bool:
    return bool(re.search(r"\d", token)) and bool(_CYR.search(token) or _LAT.search(token)) or (
        bool(_CYR.search(token)) and bool(_LAT.search(token)))


def fold_homoglyphs(text: str) -> str:
    """Fold Cyrillic look-alikes to Latin inside code-like tokens only (А500C, Мtv-1)."""
    def fix(m):
        tok = m.group(0)
        return tok.translate(HOMOGLYPHS) if is_code_like(tok) else tok
    return _CODE_TOKEN.sub(fix, text)


UNIT_MAP = {
    "m3": "m³", "m(3)": "m³", "m³": "m³", "м3": "m³", "kub.m": "m³",
    "m2": "m²", "m(2)": "m²", "m²": "m²", "м2": "m²", "kv.m": "m²",
    "m": "m", "p/m": "m", "pagon metr": "m", "p.m": "m", "pm": "m", "pm.": "m", "p.m.": "m", "metr": "m",
    "km": "km",
    "ədəd": "each", "əd": "each", "əd.": "each", "ed": "each", "ədəd.": "each",
    "dəst": "set", "komplekt": "set", "компл": "set", "kompl": "set",
    "ton": "t", "t": "t", "tn": "t",
    "kq": "kg", "kg": "kg",
}


def canonical_unit(raw) -> tuple[str, bool]:
    """Canonical unit and whether it was recognised. Unknown units are returned as written."""
    if raw is None:
        return "", False
    key = re.sub(r"\s+", " ", str(raw)).strip().lower()
    if key in UNIT_MAP:
        return UNIT_MAP[key], True
    return str(raw).strip(), False


_NUM = re.compile(r"(?<![\d.,])[-+]?\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d+)?|[-+]?\d+(?:[.,]\d+)?")


def parse_number(tok: str) -> float | None:
    t = tok.replace("\u00a0", " ").strip()
    if re.fullmatch(r"[-+]?\d{1,3}(?: \d{3})+(?:[.,]\d+)?", t):
        t = t.replace(" ", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def numbers_in(text: str) -> list[tuple[str, float]]:
    out = []
    for m in _NUM.finditer(text):
        v = parse_number(m.group(0))
        if v is not None:
            out.append((m.group(0), v))
    return out
