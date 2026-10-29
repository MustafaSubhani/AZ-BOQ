"""Read scanned sheets with a vision model. Review-only: nothing here feeds the matcher.

Scans have no vectors and no text layer. A transcription is a hint for a person,
so every page result carries status 'review' and the source page it came from.
Without OPENAI_API_KEY nothing is read, and each scan is logged as unread.
"""
import base64
import json
import os

import pymupdf

from . import config, runlog, store

SCAN_KINDS = ("drawing_scan", "explanatory_note_scan", "estimate_scan")
MAX_PAGES = 40
DPI = 150
PROMPT = (
    "You are reading one scanned page of an Azerbaijani construction drawing or note. "
    "Transcribe exactly what is printed; never guess or complete. Return JSON: "
    '{"sheet_number": str|null, "title": str|null, "lines": [str], '
    '"tables": [{"title": str|null, "rows": [[str]]}], "unreadable": [str]}. '
    "Keep Azerbaijani letters (ə, ı, ş, ç, ğ, ö, ü) and numbers exactly as printed, including decimal commas."
)


def _scans() -> list[dict]:
    return [f for f in store.get("register")["files"] if f["kind"] in SCAN_KINDS]


def _page_png(path: str, page: int) -> bytes:
    doc = pymupdf.open(path)
    return doc[page].get_pixmap(dpi=DPI).tobytes("png")


def _read_page(client, png: bytes) -> dict:
    b64 = base64.b64encode(png).decode()
    resp = client.chat.completions.create(
        model=config.OPENAI_VISION_MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": PROMPT},
                  {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}],
    )
    usage = getattr(resp, "usage", None)
    return {"result": json.loads(resp.choices[0].message.content), "tokens": getattr(usage, "total_tokens", None)}


def run_vision() -> dict:
    files = _scans()
    out = {"model": config.OPENAI_VISION_MODEL, "files": []}
    with runlog.stage("vision"):
        if not os.environ.get("OPENAI_API_KEY"):
            for f in files:
                out["files"].append({"sha256": f["sha256"], "rel": f["rel"], "status": "not run", "pages": [],
                                     "reason": "OPENAI_API_KEY is not set"})
                runlog.warn("vision", f"{f['name']}: scan not read (no OPENAI_API_KEY); its lines stay unchecked",
                            file=f["rel"])
            return out
        from openai import OpenAI
        client = OpenAI()
        for f in files:
            doc = pymupdf.open(f["path"])
            pages = []
            for p in range(min(len(doc), MAX_PAGES)):
                try:
                    res = _read_page(client, _page_png(f["path"], p))
                    pages.append({"page": p, "status": "review", **res})
                except Exception as exc:  # noqa: BLE001 - a failed page is recorded and shown, never skipped silently
                    pages.append({"page": p, "status": "failed", "error": repr(exc)})
                    runlog.warn("vision", f"{f['name']} page {p + 1}: vision read failed: {exc!r}", file=f["rel"])
            if len(doc) > MAX_PAGES:
                runlog.warn("vision", f"{f['name']}: only the first {MAX_PAGES} of {len(doc)} pages were read", file=f["rel"])
            out["files"].append({"sha256": f["sha256"], "rel": f["rel"], "status": "read for review", "pages": pages})
            runlog.event("vision", "info", f"{f['name']}: {len(pages)} pages transcribed for review")
    return out
