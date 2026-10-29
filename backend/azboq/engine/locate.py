"""Find things in the drawing dumps and turn them into Sources. Nothing here invents a value."""
import re
from functools import lru_cache

from .. import store
from ..dwg.read import load_dump
from ..pdf.read import load_pdf_dump
from ..text.normalise import fold_key, numbers_in
from ..values import Source


@lru_cache(maxsize=1)
def files() -> dict:
    return {f["sha256"]: f for f in store.get("register")["files"]}


@lru_cache(maxsize=1)
def sheets() -> dict:
    return store.get("sheets")


@lru_cache(maxsize=64)
def dump(sha: str) -> dict:
    return load_dump(sha)


@lru_cache(maxsize=64)
def pdf(sha: str) -> dict:
    return load_pdf_dump(sha)


def regions(sha: str) -> list[dict]:
    return sheets()["dwg"].get(sha, {}).get("regions", [])


def region_of(sha: str, at) -> dict | None:
    for r in regions(sha):
        b = r["bbox"]
        if b[0] <= at[0] <= b[2] and b[1] <= at[1] <= b[3]:
            return r
    return None


def dwg_files(name_contains: str | None = None, discipline: str | None = None) -> list[str]:
    out = []
    for sha, f in files().items():
        if f["kind"] != "drawing_cad":
            continue
        if name_contains and fold_key(name_contains) not in fold_key(f["rel"]):
            continue
        if discipline and f.get("discipline") != discipline:
            continue
        out.append(sha)
    return sorted(out, key=lambda s: files()[s]["rel"])


def pdf_files(name_contains: str | None = None) -> list[str]:
    return sorted((sha for sha, f in files().items() if f["kind"] == "drawing_pdf" and
                   (not name_contains or fold_key(name_contains) in fold_key(f["rel"]))),
                  key=lambda s: files()[s]["rel"])


def texts_in(sha: str, building: str | None = None, region_title: str | None = None):
    d = dump(sha)
    for t in d["texts"]:
        r = region_of(sha, t["at"])
        b = r["building"] if r else files()[sha].get("building")
        if building and b != building:
            continue
        if region_title and not (r and re.search(region_title, fold_key(r.get("title") or ""))):
            continue
        yield t, r


def dxf_source(sha: str, entity: dict, region: dict | None, note: str = "") -> Source:
    f = files()[sha]
    loc = {"kind": "dxf_entity", "handle": entity.get("handle"), "layer": entity.get("layer"),
           "region": region["id"] if region else None, "at": entity.get("at"),
           "sheet": (region or {}).get("number", {}) and (region or {}).get("number", {}).get("raw") if region else None}
    if note:
        loc["note"] = note
    return Source(sha, f["rel"], loc, entity.get("raw") or entity.get("text"), entity.get("text"))


def dim_source(sha: str, dim: dict, region: dict | None) -> Source:
    f = files()[sha]
    loc = {"kind": "dxf_dimension", "handle": dim.get("handle"), "layer": dim.get("layer"),
           "region": region["id"] if region else None, "at": dim.get("at"), "measurement": dim.get("measurement"),
           "override": dim.get("text") or None}
    return Source(sha, f["rel"], loc, dim.get("text") or None, f"{dim.get('measurement'):g}")


def pdf_source(sha: str, page: int, line: dict) -> Source:
    f = files()[sha]
    return Source(sha, f["rel"], {"kind": "pdf_span", "page": page, "bbox": line["bbox"]}, line.get("raw"), line["text"])


def rows(texts: list[dict], tol: float = 0.6) -> list[list[dict]]:
    """Group texts into rows by baseline. Tolerance is a fraction of the text height."""
    items = sorted(texts, key=lambda t: -t["at"][1])
    out: list[list[dict]] = []
    for t in items:
        h = t["h"] if t.get("h") else 0.0
        if out and abs(out[-1][0]["at"][1] - t["at"][1]) <= h * tol + 1e-9:
            out[-1].append(t)
        else:
            out.append([t])
    for r in out:
        r.sort(key=lambda t: t["at"][0])
    return out


def row_of(anchor: dict, texts: list[dict], tol: float = 0.6, max_dx: float | None = None) -> list[dict]:
    h = anchor["h"] if anchor.get("h") else 0.0
    ay, ax = anchor["at"][1], anchor["at"][0]
    row = [t for t in texts if abs(t["at"][1] - ay) <= h * tol and t["at"][0] >= ax - h * 0.5 and
           (max_dx is None or t["at"][0] - ax <= max_dx)]
    return sorted(row, key=lambda t: t["at"][0])


def numbers_of(text: str) -> list[float]:
    return [v for _, v in numbers_in(text)]
