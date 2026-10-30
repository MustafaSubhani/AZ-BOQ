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
    d = load_pdf_dump(sha) or {"pages": []}
    stored = (sheets() or {}).get("pdf", {}).get(sha)
    if stored:
        flags = {p.get("page"): p for p in stored.get("pages", [])}
        for page in d.get("pages", []):
            src = flags.get(page.get("page")) or {}
            for key in ("copy_of", "family", "only_other_order"):
                if src.get(key):
                    page[key] = src[key]
    return d


def regions(sha: str) -> list[dict]:
    return sheets()["dwg"].get(sha, {}).get("regions", [])


def region_of(sha: str, at) -> dict | None:
    for r in regions(sha):
        b = r["bbox"]
        if b[0] <= at[0] <= b[2] and b[1] <= at[1] <= b[3]:
            return r
    return None


def _name_has(fragment: str, rel: str) -> bool:
    """A file name contains the fragment. A following digit ('dk 2') is a different file."""
    key = fold_key(rel)
    needle = fold_key(fragment)
    start = 0
    while True:
        at = key.find(needle, start)
        if at < 0:
            return False
        rest = key[at + len(needle):].lstrip(" ._-")
        if not rest[:1].isdigit():
            return True
        start = at + 1


def dwg_files(name_contains: str | None = None, discipline: str | None = None) -> list[str]:
    out = []
    for sha, f in files().items():
        if f["kind"] != "drawing_cad":
            continue
        if name_contains and not _name_has(name_contains, f["rel"]):
            continue
        if discipline and f.get("discipline") != discipline:
            continue
        out.append(sha)
    return sorted(out, key=lambda s: files()[s]["rel"])


def pdf_files(name_contains: str | None = None) -> list[str]:
    return sorted((sha for sha, f in files().items() if f["kind"] == "drawing_pdf" and
                   (not name_contains or _name_has(name_contains, f["rel"]))),
                  key=lambda s: files()[s]["rel"])


def texts_in(sha: str, building: str | None = None, region_title: str | None = None):
    d = dump(sha)
    for t in d["texts"]:
        r = region_of(sha, t["at"])
        b = r["building"] if r else files()[sha].get("building")
        if building and b != building:
            continue
        if r and r.get("copy_of"):
            continue
        if region_title and not (r and re.search(region_title, fold_key(r.get("title") or ""))):
            continue
        yield t, r


def dxf_source(sha: str, entity: dict, region: dict | None, note: str = "") -> Source:
    f = files()[sha]
    loc = {"kind": "dxf_entity", "handle": entity.get("handle"), "layer": entity.get("layer"),
           "region": region["id"] if region else None, "at": entity.get("at"),
           "sheet": (region or {}).get("number", {}) and (region or {}).get("number", {}).get("raw") if region else None}
    if entity.get("table"):
        loc["table"] = entity["table"]
    if region and region.get("only_other_order"):
        loc["only_other_order"] = True
    if note:
        loc["note"] = note
    return Source(sha, f["rel"], loc, entity.get("raw") or entity.get("text"), entity.get("text"))


def dim_source(sha: str, dim: dict, region: dict | None) -> Source:
    f = files()[sha]
    loc = {"kind": "dxf_dimension", "handle": dim.get("handle"), "layer": dim.get("layer"),
           "region": region["id"] if region else None, "at": dim.get("at"), "measurement": dim.get("measurement"),
           "override": dim.get("text") or None}
    if region and region.get("only_other_order"):
        loc["only_other_order"] = True
    return Source(sha, f["rel"], loc, dim.get("text") or None, f"{dim.get('measurement'):g}")


def pdf_source(sha: str, page: int, line: dict) -> Source:
    f = files()[sha]
    loc = {"kind": "pdf_span", "page": page, "bbox": line["bbox"]}
    pages = pdf(sha).get("pages") or []
    if 0 <= page < len(pages) and pages[page].get("only_other_order"):
        loc["only_other_order"] = True
    return Source(sha, f["rel"], loc, line.get("raw"), line["text"])


def _yspan(t) -> tuple[float, float]:
    """Vertical extent. An MTEXT box is used when the reader stored one; otherwise the insert and the height."""
    box = t.get("bbox")
    if box and len(box) == 4 and not t.get("bbox_estimated"):
        return min(box[1], box[3]), max(box[1], box[3])
    y = t["at"][1]
    h = t["h"] if t.get("h") else 0.0
    return y - h * 0.35, y + h * 0.35


def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return min(a[1], b[1]) - max(a[0], b[0]) > 1e-6


def rows(texts: list[dict], tol: float = 0.6) -> list[list[dict]]:
    """Group texts into rows by overlapping boxes. `tol` remains for callers that have no boxes."""
    del tol
    items = sorted(texts, key=lambda t: -_yspan(t)[1])
    bands: list[list] = []
    for t in items:
        span = _yspan(t)
        if bands and _overlaps(bands[-1][0], span):
            prev = bands[-1][0]
            bands[-1][0] = (min(prev[0], span[0]), max(prev[1], span[1]))
            bands[-1][1].append(t)
        else:
            bands.append([span, [t]])
    out = []
    for _span, members in bands:
        members.sort(key=lambda t: t["at"][0])
        out.append(members)
    return out


def row_of(anchor: dict, texts: list[dict], tol: float = 0.6, max_dx: float | None = None) -> list[dict]:
    del tol
    span = _yspan(anchor)
    ax = anchor["at"][0]
    h = anchor["h"] if anchor.get("h") else 0.0
    row = [t for t in texts if _overlaps(_yspan(t), span) and t["at"][0] >= ax - h * 0.5 and
           (max_dx is None or t["at"][0] - ax <= max_dx)]
    return sorted(row, key=lambda t: t["at"][0])


def numbers_of(text: str) -> list[float]:
    return [v for _, v in numbers_in(text)]
