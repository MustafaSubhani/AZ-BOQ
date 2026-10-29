"""File register: every file in the package with its hash, kind, discipline, building and order.

Classification here is by name and folder. Sheet-level classification from title
blocks (sheets.py) refines it after the drawings are read, because one file can
hold several buildings and file names do not always say what is inside.
"""
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pymupdf

from .. import config, runlog
from ..hashing import sha256
from ..text.normalise import fold_key

DWG_VERSIONS = {"AC1015": "R2000", "AC1018": "R2004", "AC1021": "R2007", "AC1024": "R2010", "AC1027": "R2013",
                "AC1032": "R2018"}

BUILDINGS = [
    (r"transform|ktm|kty|9526", "substation"),
    (r"\(son\)|deposu|9335 mh\.pdf|elektrik\.dwg|-01- iv|depo 2-ci|depo son|istilik itki|izolyasiya|enerji", "depot"),
    (r"qulle|telim", "tower"),
    (r"nezaret|nbm", "guard_room"),
    (r"nasos", "pump_station"),
    (r"istilik|qazanxana", "heating_point"),
    (r"ayaqyolu", "toilet"),
    (r"avtoyuma", "vehicle_wash"),
    (r"icmeli", "drinking_tanks"),
    (r"yangin su anbari|81m", "fire_tanks"),
    (r"sohbetgah", "gazebo"),
    (r"generator", "generator"),
    (r"istinad|hasar", "fence"),
    (r"bas plan|dynx|vertikalka|\baq\b|pos|taprq|dqt|0\.4kv|ee\.pdf", "site"),
]
DISCIPLINES = [
    (r"smeta", "estimate"),
    (r"\.lir$", "structure"),
    (r"\bdk\b|dk son|dk\.dwg|\bdk\.pdf|su anbari.*\.pdf|altliq", "structure"),
    (r"\bsk\b|-sk|xsk", "water_sewer"),
    (r"\biv\b|istilik itki|izolyasiya|enerji", "hvac"),
    (r"elektrik|\bee\b|ktm|kty|generator|nasosxana|\bat\.pdf|nbm|qulle 9335|eys", "electrical"),
    (r"vertikalka|dynx|bas plan|\baq\b|bp\.pdf|qazanxana ve", "site"),
    (r"pos|taprq|dqt", "construction_org"),
    (r"\bmh\b|mh\.pdf|ayaqyolu\.pdf|otagi\.pdf|qulle\.pdf|stansiyasi\.pdf|menteqesi\.pdf|yrs - vn|yrs - vm", "architecture"),
    (r"izahat", "explanatory_note"),
    (r"ekalog", "ecology"),
    (r"hesabat|iqlim|geologiya", "geology"),
    (r"titul|tutul", "title"),
]


def _key(path: Path) -> str:
    """Name first, then the folder path below the package root, as one folded string."""
    rel = path.relative_to(config.DATA_DIR)
    parts = [p for p in rel.parts[:-1] if fold_key(p) != fold_key(config.PACKAGE_DIR.name)]
    return fold_key(unicodedata.normalize("NFC", path.name)), fold_key(unicodedata.normalize("NFC", "/".join(parts)))


def _first(rules, name_key: str, folder_key: str, default: str) -> str:
    for text in (name_key, folder_key):
        for pat, value in rules:
            if re.search(pat, text):
                return value
    return default


def junk_reason(path: Path) -> str | None:
    name = path.name
    if name.startswith("~$"):
        return "Word lock file"
    if path.suffix.lower() == ".bak":
        return "AutoCAD backup"
    if path.suffix.lower() == ".log":
        return "Plot log"
    if path.suffix.lower() == ".zip":
        return "Zip of the same folder"
    return None


def _pdf_info(path: Path) -> dict:
    doc = pymupdf.open(path)
    chars = sum(len(p.get_text()) for p in doc)
    pages = doc.page_count
    return {"pages": pages, "text_chars": chars, "scanned": chars < 40 * pages}


def classify(path: Path) -> dict:
    name_key, folder_key = _key(path)
    key = f"{name_key} {folder_key}"
    ext = path.suffix.lower()
    row = {"path": str(path), "rel": path.relative_to(config.DATA_DIR).as_posix(), "name": path.name,
           "ext": ext, "size": path.stat().st_size}
    junk = junk_reason(path)
    if junk:
        row.update(kind="junk", junk_reason=junk)
        return row
    if path == config.BILL_PATH:
        row.update(kind="contract_bill", discipline="bill", building="all", order="9335")
        return row
    if path == config.BILL_PDF_PATH:
        row.update(kind="contract_bill_print", discipline="bill", building="all", order="9335",
                   note="Print of the Excel bill. The Excel is read, not this PDF.")
        return row
    if ext == ".dwg":
        with open(path, "rb") as f:
            ver = f.read(6).decode("latin1")
        row.update(kind="drawing_cad", dwg_version=DWG_VERSIONS.get(ver, ver))
    elif ext == ".pdf":
        info = _pdf_info(path)
        row.update(info)
        if "smeta" in key:
            row["kind"] = "estimate_scan"
        elif "izahat" in key:
            row["kind"] = "explanatory_note_scan" if info["scanned"] else "explanatory_note"
        else:
            row["kind"] = "drawing_scan" if info["scanned"] else "drawing_pdf"
    elif ext in (".doc", ".docx"):
        row["kind"] = "narrative"
    elif ext == ".lir":
        row["kind"] = "analysis_model"
        row["note"] = "LIRA-SAPR calculation model. Not a quantity source."
    else:
        row["kind"] = "other"
    row["order"] = "9526" if "9526" in key else "9335"
    row["discipline"] = _first(DISCIPLINES, name_key, folder_key, "unknown")
    row["building"] = _first(BUILDINGS, name_key, folder_key, "site")
    return row


def build_register() -> dict:
    files = sorted(p for p in config.DATA_DIR.rglob("*") if p.is_file())
    rows = []
    with runlog.stage("ingest"):
        for p in files:
            row = classify(p)
            row["sha256"] = sha256(p)
            rows.append(row)
        by_hash = defaultdict(list)
        for row in rows:
            if row["kind"] != "junk":
                by_hash[row["sha256"]].append(row)
        groups = []
        for h, members in by_hash.items():
            if len(members) > 1:
                members.sort(key=lambda r: (len(r["rel"]), r["rel"]))
                canon = members[0]
                for m in members[1:]:
                    m["duplicate_of"] = canon["rel"]
                groups.append({"sha256": h, "canonical": canon["rel"], "copies": [m["rel"] for m in members[1:]]})
        for row in rows:
            if row.get("discipline") == "unknown" and row["kind"] not in ("junk",):
                runlog.warn("ingest", f"discipline not recognised: {row['rel']}", file=row["rel"])
        counts = defaultdict(int)
        for row in rows:
            counts[row["kind"]] += 1
        runlog.event("ingest", "info", f"{len(rows)} files, {counts['junk']} junk, {len(groups)} duplicate groups")
    return {"files": rows, "duplicates": groups, "counts": dict(counts), "total": len(rows)}
