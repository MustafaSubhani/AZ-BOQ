"""Layer names: strip plot and lineweight suffixes, fold look-alikes, map the stem to a role."""
import re
import unicodedata
from functools import lru_cache

import yaml

from .. import config
from ..text.legacy import decode

_PEN = re.compile(r"(_Ном\._?пера__\d+|_Ном_пера__\d+|_Pen_No__\d+)+$", re.I)
_WEIGHT = re.compile(r"\s+0[.,]\d+\s*$")
# Azerbaijani Latin never uses these. They are Cyrillic read back through the wrong code page.
_NOT_AZ_LATIN = re.compile(r"[àáâãåæèéêëìíîïðñòóôõøùúûýþÿÀÁÂÃÅÆÈÉÊËÌÍÎÏÐÑÒÓÔÕØÙÚÛÝÞ]")


def fix_mojibake(name: str) -> str:
    """Repair a layer name that is Cyrillic stored as cp1254 or cp1252. Real Azerbaijani names stay as written."""
    if not name or not _NOT_AZ_LATIN.search(name) or "ə" in name or "Ə" in name:
        return name
    for wrong in ("cp1254", "cp1252"):
        try:
            cand = name.encode(wrong).decode("cp1251")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if re.search(r"[\u0400-\u04FF]", cand) and not _NOT_AZ_LATIN.search(cand):
            return cand
    return name


def stem(name: str) -> str:
    s = unicodedata.normalize("NFC", name or "")
    prev = None
    while prev != s:
        prev = s
        s = _PEN.sub("", s)
        s = _WEIGHT.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def _rules():
    rows = yaml.safe_load((config.RULES_DIR / "layer_roles.yaml").read_text(encoding="utf-8")) or []
    return [(re.compile(r["pattern"]), r["role"]) for r in rows]


@lru_cache(maxsize=4096)
def role(name: str) -> str:
    s = stem(name)
    fixed = fix_mojibake(s)
    decoded = decode(fixed).text
    for pat, r in _rules():
        if pat.search(s) or pat.search(fixed) or pat.search(decoded):
            return r
    return "unclassified"
