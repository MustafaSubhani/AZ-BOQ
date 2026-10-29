"""Text-layer PDFs: lines of text with their bounding boxes, decoded span by span by font."""
import json
import re

import pymupdf

from .. import config, runlog
from ..sheets import classify_sheet, STAMP_WORDS
from ..text.legacy import decode
from ..text.normalise import fold_homoglyphs


def dump_pdf(path, file_building: str, file_discipline: str) -> dict:
    doc = pymupdf.open(path)
    pages = []
    for pno, page in enumerate(doc):
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                raw_parts, dec_parts, fonts, schemes = [], [], [], set()
                for span in line["spans"]:
                    t = span["text"]
                    if not t:
                        continue
                    font = span["font"].split("+", 1)[-1]
                    d = decode(t, font)
                    raw_parts.append(t)
                    dec_parts.append(d.text)
                    if d.scheme != "unicode":
                        schemes.add(d.scheme)
                    if font not in fonts:
                        fonts.append(font)
                text = re.sub(r"\s+", " ", "".join(dec_parts)).strip()
                if not text:
                    continue
                lines.append({"text": text, "code_text": fold_homoglyphs(text), "raw": "".join(raw_parts),
                              "bbox": [round(v, 1) for v in line["bbox"]], "fonts": fonts,
                              "scheme": (schemes.pop() if len(schemes) == 1 else ("mixed" if schemes else "unicode"))})
        w, h = page.rect.width, page.rect.height
        stamp = [l["text"] for l in lines if l["bbox"][0] > w * 0.55 and l["bbox"][1] > h * 0.7]
        stamp_any = [l["text"] for l in lines if STAMP_WORDS.search(l["text"])]
        info = classify_sheet(stamp + stamp_any, file_building, file_discipline)
        pages.append({"page": pno, "width": w, "height": h, "lines": lines, **info})
    return {"pdf": str(path), "pages": pages, "page_count": doc.page_count}


def pdf_dump_path(file_sha: str):
    return config.CACHE_DIR / "pdf" / f"{file_sha[:12]}.json"


def load_pdf_dump(file_sha: str):
    p = pdf_dump_path(file_sha)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def dump_all_pdfs(register: dict, force: bool = False) -> dict:
    out = {}
    with runlog.stage("read_pdf"):
        for f in register["files"]:
            if f["kind"] != "drawing_pdf":
                continue
            target = pdf_dump_path(f["sha256"])
            if target.exists() and not force:
                out[f["sha256"]] = str(target)
                continue
            data = dump_pdf(f["path"], f.get("building", "site"), f.get("discipline", "unknown"))
            data["file"] = f["rel"]
            data["sha256"] = f["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            n = sum(len(p["lines"]) for p in data["pages"])
            legacy = sum(1 for p in data["pages"] for l in p["lines"] if l["scheme"] != "unicode")
            runlog.event("read_pdf", "info", f"{f['name']}: {data['page_count']} pages, {n} lines, {legacy} legacy-decoded")
            out[f["sha256"]] = str(target)
    return out
