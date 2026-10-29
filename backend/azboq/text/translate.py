"""Display-layer translation. Stored data and exports stay Azerbaijani.

A translation is cached by the hash of its source, prompt version and glossary
version. Every answer is checked: numbers and codes must survive unchanged and
glossary terms must appear in their approved form. Corrections made by a person
are stored with origin "human" and always win.
"""
import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from functools import lru_cache

import yaml

from .. import config, runlog
from .normalise import match_key

PROMPT_VERSION = 1
BATCH = 50
SYSTEM_PROMPT = (
    "You translate Azerbaijani construction-bill and drawing text into English for a quantity surveyor. "
    "Keep every number, unit, code, mark, dimension and standard name (SNiP, GOST, AzDTN, ГОСТ) exactly as written. "
    "Use the glossary terms given. Do not add or explain. Some input has keyboard typos such as ';' for 'ı'; "
    "translate the meaning. Return JSON: {\"items\": [{\"id\": int, \"en\": str}]}."
)


@lru_cache(maxsize=1)
def glossary() -> dict:
    data = yaml.safe_load(config.GLOSSARY_PATH.read_text(encoding="utf-8"))
    return {"version": data["version"], "terms": data["terms"]}


def _hash(text: str, lang: str) -> str:
    g = glossary()["version"]
    return hashlib.sha256(f"{lang}|{PROMPT_VERSION}|{g}|{text}".encode("utf-8")).hexdigest()


@contextmanager
def _db():
    config.ensure_dirs()
    con = sqlite3.connect(config.TRANSLATIONS_DB)
    con.execute("create table if not exists translation (h text primary key, source text, lang text, text text, "
                "origin text, model text, checks text, created_at real)")
    try:
        yield con
        con.commit()
    finally:
        con.close()


_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[A-Za-zƏəİıÖöÜüÇçŞşĞğ]*\d[\w\-./]*")


def protected_tokens(text: str) -> list[str]:
    return sorted(t.replace(",", ".") for t in _TOKEN.findall(text))


def check(source: str, target: str) -> dict:
    src, tgt = protected_tokens(source), protected_tokens(target)
    missing_terms = []
    key = match_key(source)
    for az, en in glossary()["terms"].items():
        if len(az) > 4 and match_key(az) in key and en.lower() not in target.lower():
            missing_terms.append(az)
    ratio = (len(target) + 1) / (len(source) + 1)
    ok_numbers = src == tgt
    return {"numbers_ok": ok_numbers, "missing_terms": missing_terms[:5], "length_ratio": round(ratio, 2),
            "ok": ok_numbers and 0.4 <= ratio <= 3.5}


def glossary_translate(text: str) -> str | None:
    """Translate only when glossary phrases cover every word; else None."""
    terms = sorted(glossary()["terms"].items(), key=lambda kv: -len(kv[0]))
    out = text
    for az, en in terms:
        out = re.sub(re.escape(az), en, out, flags=re.IGNORECASE)
    leftover = re.sub(r"[\d\s.,:;()\-/=³²×x\"'«»]+", " ", out)
    words = [w for w in leftover.split() if re.search(r"[A-Za-zƏəİıÖöÜüÇçŞşĞğ]", w)]
    en_words = {w.lower() for en in glossary()["terms"].values() for w in re.findall(r"[A-Za-z]+", en)}
    if all(w.lower().strip("()") in en_words or w.lower() in ("m", "kv", "m³", "and", "of") for w in words):
        return re.sub(r"\s+", " ", out).strip()
    return None


def lookup(texts: list[str], lang: str = "en") -> dict:
    out = {}
    with _db() as con:
        for t in texts:
            row = con.execute("select text, origin, model, checks from translation where h = ?",
                              (_hash(t, lang),)).fetchone()
            if row:
                out[t] = {"text": row[0], "origin": row[1], "model": row[2], "checks": json.loads(row[3] or "{}")}
                continue
            g = glossary_translate(t)
            if g:
                out[t] = {"text": g, "origin": "glossary", "model": None, "checks": check(t, g)}
            else:
                out[t] = {"text": None, "origin": "pending", "model": None, "checks": {}}
    return out


def save(source: str, text: str, origin: str, model: str | None, checks: dict, lang: str = "en"):
    with _db() as con:
        con.execute("insert or replace into translation values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (_hash(source, lang), source, lang, text, origin, model, json.dumps(checks), time.time()))


def correct(source: str, text: str):
    save(source, text, "human", None, check(source, text))


def _openai_batch(client, items: list[tuple[int, str]]) -> dict:
    gl = glossary()["terms"]
    hits = {az: en for az, en in gl.items() if any(match_key(az) in match_key(t) for _, t in items)}
    user = json.dumps({"glossary": hits, "items": [{"id": i, "az": t} for i, t in items]}, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=config.OPENAI_TRANSLATION_MODEL, temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
    )
    data = json.loads(resp.choices[0].message.content)
    usage = getattr(resp, "usage", None)
    runlog.event("translate", "info", f"batch of {len(items)}", tokens=getattr(usage, "total_tokens", None))
    return {int(x["id"]): x["en"] for x in data.get("items", [])}


def collect_strings() -> list[str]:
    from .. import store
    seen, out = set(), []

    def add(s):
        s = (s or "").strip()
        if len(s) >= 3 and re.search(r"[A-Za-zƏəİıÖöÜüÇçŞşĞğ\u0400-\u04FF]", s) and s not in seen:
            seen.add(s)
            out.append(s)

    bill = store.get("bill") or {"sections": [], "lines": []}
    for s in bill["sections"]:
        add(s["title"])
    for l in bill["lines"]:
        add(l["description"])
        add(l.get("comment"))
    return out


def prewarm(limit: int | None = None) -> dict:
    strings = collect_strings()
    pending = [s for s, v in lookup(strings).items() if v["origin"] == "pending"]
    if limit:
        pending = pending[:limit]
    if not os.environ.get("OPENAI_API_KEY"):
        runlog.warn("translate", f"OPENAI_API_KEY not set; {len(pending)} strings stay in Azerbaijani until a key is set")
        return {"pending": len(pending), "translated": 0}
    from openai import OpenAI
    client = OpenAI()
    done = 0
    with runlog.stage("translate"):
        for i in range(0, len(pending), BATCH):
            chunk = list(enumerate(pending[i:i + BATCH]))
            result = _openai_batch(client, chunk)
            retry = []
            for j, src in chunk:
                en = result.get(j)
                c = check(src, en) if en else {"ok": False}
                if en and c["ok"]:
                    save(src, en, "llm", config.OPENAI_TRANSLATION_MODEL, c)
                    done += 1
                else:
                    retry.append((j, src))
            if retry:
                again = _openai_batch(client, retry)
                for j, src in retry:
                    en = again.get(j)
                    c = check(src, en) if en else {"ok": False}
                    origin = "llm" if en and c["ok"] else "needs_check"
                    if en:
                        save(src, en, origin, config.OPENAI_TRANSLATION_MODEL, c)
                        done += origin == "llm"
    return {"pending": len(pending) - done, "translated": done}
