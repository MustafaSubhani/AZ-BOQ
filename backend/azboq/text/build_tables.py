"""Derive legacy-font decode tables from the fonts embedded in the package PDFs.

Legacy Azerbaijani fonts draw Latin Azerbaijani letters at Cyrillic code points.
For every embedded font whose name matches the legacy pattern, each glyph sitting
at a Cyrillic slot is rendered and compared with reference letters drawn in the
installed Arial or Times New Roman. The best pixel match (IoU) is the letter the
font actually draws. A contact sheet image is written for a quick eye check.
"""
import io
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from fontTools.ttLib import TTFont

from .. import config, runlog

LEGACY_FONT_RE = re.compile(r"(?i)azlat|azerilat|azericyr|azcyr|\(la\)|a3ti|a2ti|a3times|a3arial|arialcyr|a3arialrus")
LATIN_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZƏÖÜÇŞĞİ"
LATIN_LOWER = "abcdefghijklmnopqrstuvwxyzəöüçşğı"
CYR_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯҒҜҸӘӨҮҺЈ"
CYR_LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяғҝҹәөүһј"
WIN_FONTS = Path("C:/Windows/Fonts")
SIZE = 72
BOX = 96
CYRILLIC_MARGIN = 0.08


def family_of(basefont: str) -> str:
    name = basefont.split("+", 1)[-1]
    name = re.sub(r"(?i)[-,]?(bold|italic|oblique|mt)$", "", name)
    name = re.sub(r"(?i)(bold|italic)$", "", name)
    return name


def _reference_font(family: str) -> Path:
    if re.search(r"(?i)times", family):
        return WIN_FONTS / "times.ttf"
    if re.search(r"(?i)narrow", family):
        return WIN_FONTS / "ARIALN.TTF"
    return WIN_FONTS / "arial.ttf"


def _render(fontbuffer: bytes | None, fontfile: str | None, ch: str) -> np.ndarray | None:
    doc = pymupdf.open()
    page = doc.new_page(width=BOX, height=BOX)
    kw = {"fontbuffer": fontbuffer} if fontbuffer else {"fontfile": fontfile}
    page.insert_font(fontname="G", **kw)
    page.insert_text((12, 74), ch, fontsize=SIZE, fontname="G")
    pix = page.get_pixmap(dpi=72, colorspace=pymupdf.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    mask = arr < 128
    if mask.sum() < 4:
        return None
    cols = np.where(mask.any(axis=0))[0]
    shifted = np.zeros_like(mask)
    width = cols[-1] - cols[0] + 1
    start = (BOX - width) // 2
    shifted[:, start:start + width] = mask[:, cols[0]:cols[-1] + 1]
    return shifted


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union) if union else 0.0


_ref_cache: dict = {}


def _references(ref_font: Path, upper: bool) -> dict:
    key = (str(ref_font), upper)
    if key not in _ref_cache:
        letters = (LATIN_UPPER + CYR_UPPER) if upper else (LATIN_LOWER + CYR_LOWER)
        refs = {}
        for ch in letters:
            img = _render(None, str(ref_font), ch)
            if img is not None:
                refs[ch] = img
        _ref_cache[key] = refs
    return _ref_cache[key]


def table_for_font(buf: bytes, family: str) -> dict:
    tt = TTFont(io.BytesIO(buf))
    cmap = tt.getBestCmap() or {}
    glyph_to_code = {}
    for t in tt["cmap"].tables:
        for code, glyph in t.cmap.items():
            glyph_to_code.setdefault(glyph, code)
    for code, glyph in cmap.items():
        glyph_to_code[glyph] = code
    ref_font = _reference_font(family)
    out = {}
    for glyph in tt.getGlyphOrder():
        m = re.fullmatch(r"uni(04[0-9A-F]{2})", glyph)
        if not m or glyph not in glyph_to_code:
            continue
        slot = chr(int(m.group(1), 16))
        img = _render(buf, None, chr(glyph_to_code[glyph]))
        if img is None:
            continue
        refs = _references(ref_font, slot.isupper())
        cyr = CYR_UPPER + CYR_LOWER
        latin = sorted(((_iou(img, r), ch) for ch, r in refs.items() if ch not in cyr), reverse=True)
        cyrillic = sorted(((_iou(img, r), ch) for ch, r in refs.items() if ch in cyr), reverse=True)
        # Latin and Cyrillic twins (A/А, Ə/Ә, H/Н) render identically; a Cyrillic
        # reading wins only when it fits clearly better than every Latin letter.
        if cyrillic and cyrillic[0][0] > latin[0][0] + CYRILLIC_MARGIN:
            best, second = cyrillic[0], latin[0]
        else:
            best, second = latin[0], latin[1]
        out[slot] = {"to": best[1], "score": round(best[0], 3), "second": second[1], "second_score": round(second[0], 3)}
    return out


def build_all() -> dict:
    families: dict[str, dict] = defaultdict(dict)
    seen = set()
    pdfs = sorted(p for p in config.PACKAGE_DIR.rglob("*.pdf"))
    sheet_rows = []
    with runlog.stage("fonts"):
        for pdf in pdfs:
            doc = pymupdf.open(pdf)
            for pno in range(doc.page_count):
                for xref, _ext, _ftype, basefont, _name, _enc in doc[pno].get_fonts(full=False):
                    if xref in seen or not LEGACY_FONT_RE.search(basefont):
                        continue
                    seen.add((pdf.name, xref))
                    try:
                        _fname, _fext, _t, buf = doc.extract_font(xref)
                    except Exception as exc:
                        runlog.warn("fonts", f"cannot extract {basefont} from {pdf.name}: {exc}")
                        continue
                    if not buf:
                        continue
                    fam = family_of(basefont)
                    try:
                        table = table_for_font(buf, fam)
                    except (KeyError, Exception) as exc:
                        runlog.event("fonts", "info", f"skipped {basefont} in {pdf.name}: no usable cmap ({type(exc).__name__})")
                        continue
                    for slot, row in table.items():
                        prev = families[fam].get(slot)
                        if prev is None or row["score"] > prev["score"]:
                            families[fam][slot] = {**row, "pdf": pdf.name, "page": pno}
                            sheet_rows.append((fam, slot, row["to"], row["score"], buf))
        config.LEGACY_FONT_DIR.mkdir(parents=True, exist_ok=True)
        for fam, table in families.items():
            (config.LEGACY_FONT_DIR / f"{fam}.json").write_text(
                json.dumps(dict(sorted(table.items())), ensure_ascii=False, indent=1), encoding="utf-8")
            weak = [s for s, r in table.items() if r["score"] < 0.55]
            runlog.event("fonts", "info", f"{fam}: {len(table)} slots, {len(weak)} weak matches")
        _contact_sheet(families)
    return families


def _contact_sheet(families: dict):
    doc = pymupdf.open()
    page = doc.new_page(width=1000, height=60 + 30 * sum((len(t) // 12 + 2) for t in families.values()))
    y = 30
    for fam, table in sorted(families.items()):
        page.insert_text((20, y), f"{fam}: slot -> letter (match score)", fontsize=11)
        y += 22
        x = 20
        for slot, row in sorted(table.items()):
            page.insert_text((x, y), f"{slot}→{row['to']} {row['score']:.2f}", fontsize=10, fontfile=str(WIN_FONTS / "arial.ttf"),
                             fontname="A")
            x += 80
            if x > 940:
                x = 20
                y += 18
        y += 30
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    page.get_pixmap(dpi=90).save(str(config.CACHE_DIR / "legacy-font-contact-sheet.png"))
