"""Layer names: strip plot and lineweight suffixes, fold look-alikes, map the stem to a role."""
import re
import unicodedata
from functools import lru_cache

import yaml

from .. import config
from ..text.legacy import decode

_PEN = re.compile(r"(_Ном\._?пера__\d+|_Ном_пера__\d+|_Pen_No__\d+)+$", re.I)
_WEIGHT = re.compile(r"\s+0[.,]\d+\s*$")


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
    decoded = decode(s).text
    for pat, r in _rules():
        if pat.search(s) or pat.search(decoded):
            return r
    return "unclassified"
