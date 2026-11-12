"""Page images for the viewer. The raw package (data/) is not deployed, so they are built once and shipped in cache/."""
from pathlib import Path

import pymupdf

from .. import config
from ..crops import PDF_DPI


def tile_path(f: dict, page: int) -> Path:
    return config.TILES_DIR / f"{f['sha256'][:12]}_p{page}.png"


def page_tile(f: dict, page: int) -> Path:
    """The stored image of a page, drawn from the source PDF when it is missing."""
    out = tile_path(f, page)
    if not out.exists():
        src = config.DATA_DIR / f["rel"]
        if not src.exists():
            raise FileNotFoundError(src)
        with pymupdf.open(src) as doc:
            doc[page].get_pixmap(dpi=PDF_DPI).save(str(out))
    return out


def render_all(register: dict, progress=lambda m: None) -> dict:
    res = {"files": 0, "pages": 0, "failed": []}
    for f in register["files"]:
        src = config.DATA_DIR / f["rel"]
        if src.suffix.lower() != ".pdf":
            continue
        if not src.exists():
            res["failed"].append({"file": f["rel"], "reason": "source PDF not found"})
            continue
        with pymupdf.open(src) as doc:
            count = len(doc)
        for page in range(count):
            page_tile(f, page)
        res["files"] += 1
        res["pages"] += count
        progress(f"{f['rel']}: {count} pages")
    return res
