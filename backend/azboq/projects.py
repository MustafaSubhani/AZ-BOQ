"""Multi-project workspace registry & self-serve DWG / PDF / BOQ package ingestion."""
import hashlib
import json
import re
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path

from . import config, store

SCHEMA = """create table if not exists project_package (
    id text primary key,
    name text not null,
    order_code text not null,
    location text not null,
    client text not null,
    status text not null,
    created_at real not null,
    summary_json text not null
)"""

DWG_VERSIONS = {
    b"AC1015": "AutoCAD 2000",
    b"AC1018": "AutoCAD 2004",
    b"AC1021": "AutoCAD 2007",
    b"AC1024": "AutoCAD 2010",
    b"AC1027": "AutoCAD 2013",
    b"AC1032": "AutoCAD 2018+",
}


def _connect():
    config.ensure_dirs()
    con = sqlite3.connect(config.DB_PATH)
    con.execute(SCHEMA)
    return con


_PROJECT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:36] or "project") + f"-{int(time.time()) % 100000}"


def _safe_zip_parts(name: str) -> list[str] | None:
    """Keep a zip entry inside the extract folder. Skip directories and path escapes."""
    raw = name.replace("\\", "/")
    if not raw or raw.endswith("/"):
        return None
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        return None
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    return parts


def _inspect_file(path: Path, rel_name: str) -> dict:
    ext = path.suffix.lower()
    size = path.stat().st_size
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]

    if ext in (".bak", ".log") or path.name.startswith("~$"):
        return {"name": rel_name, "kind": "ignored", "detail": "Backup / plot log ignored", "size": size, "sha": sha}

    if ext == ".dwg":
        head = path.read_bytes()[:6]
        ver = DWG_VERSIONS.get(head, head.decode("latin1", errors="replace"))
        return {"name": rel_name, "kind": "dwg", "detail": f"CAD drawing ({ver})", "size": size, "sha": sha}

    if ext == ".dxf":
        return {"name": rel_name, "kind": "dxf", "detail": "ASCII/Binary DXF model", "size": size, "sha": sha}

    if ext == ".pdf":
        detail = "PDF document"
        kind = "pdf"
        try:
            import pymupdf
            doc = pymupdf.open(str(path))
            pages = doc.page_count
            text_pages = sum(1 for p in doc if len((p.get_text("text") or "").strip()) > 40)
            doc.close()
            if text_pages == 0 and pages > 0:
                kind = "scan"
                detail = f"Raster scan ({pages} p., OCR/review required)"
            else:
                detail = f"Vector PDF ({pages} p., {text_pages} with text)"
        except Exception:
            pass
        return {"name": rel_name, "kind": kind, "detail": detail, "size": size, "sha": sha}

    if ext in (".xlsx", ".xls"):
        detail = "Excel BOQ workbook"
        rows_count = 0
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if any(c is not None and str(c).strip() != "" for c in row):
                    rows_count += 1
            wb.close()
            detail = f"BOQ spreadsheet ({rows_count} non-empty rows)"
        except Exception:
            pass
        return {"name": rel_name, "kind": "boq_xlsx", "detail": detail, "rows": rows_count, "size": size, "sha": sha}

    return {"name": rel_name, "kind": "doc", "detail": f"Supporting file ({ext or 'file'})", "size": size, "sha": sha}


def _baseline_hadrut_project() -> dict:
    reg = store.get("register") or {"files": []}
    bill = store.get("bill") or {"lines": [], "totals": {}, "line_sum": 0}
    rep = store.get("report") or {"counts": {}, "value_by_status": {}, "total_value": 0}
    files = reg.get("files") or []
    dwg_n = sum(1 for f in files if f.get("kind") == "drawing_cad")
    pdf_n = sum(1 for f in files if f.get("kind") == "drawing_pdf")
    scan_n = sum(1 for f in files if f.get("kind") == "drawing_scan")
    counts = rep.get("counts") or {}
    checked = (counts.get("matched") or 0) + (counts.get("printed") or 0) + (counts.get("derived") or 0)
    v_status = rep.get("value_by_status") or {}
    v_checked = (v_status.get("matched") or 0) + (v_status.get("printed") or 0) + (v_status.get("derived") or 0)
    total_v = rep.get("total_value") or bill.get("line_sum") or 0

    return {
        "id": "hadrut-9335",
        "name": "Hadrut 4-Bay Fire Protection Depot",
        "order_code": "Sifariş № 9335",
        "location": "Hadrut, Xocavənd",
        "client": "FHN Capital Construction Department",
        "status": "active",
        "builtin": True,
        "created_at": 1761120000.0,
        "summary": {
            "dwg_count": dwg_n,
            "pdf_count": pdf_n,
            "scan_count": scan_n,
            "boq_lines": len(bill.get("lines") or []),
            "contract_azn": bill.get("totals", {}).get("contract_price_c5", 3811193.36),
            "backed_lines": checked,
            "contradictions": counts.get("different") or 0,
            "backed_pct": round((v_checked / total_v) * 100, 1) if total_v else 0.0,
            "oda_available": config.ODA_EXE.exists(),
            "stages": [
                {"step": "Package Ingest & SHA-256", "state": "done", "note": f"{len(files)} files classified"},
                {"step": "ODA + LibreDWG Conversion", "state": "done", "note": f"{dwg_n} DWG models verified"},
                {"step": "Schedule & Geometry Takeoff", "state": "done", "note": "51 items · Depot gate passed"},
                {"step": "BOQ Reconciliation", "state": "done", "note": f"{checked} backed · {counts.get('different', 0)} contradictions"},
            ],
            "files": [],
        },
    }


def list_projects() -> list[dict]:
    out = [_baseline_hadrut_project()]
    con = _connect()
    try:
        rows = con.execute(
            "select id, name, order_code, location, client, status, created_at, summary_json "
            "from project_package order by created_at desc"
        ).fetchall()
        for r in rows:
            out.append({
                "id": r[0],
                "name": r[1],
                "order_code": r[2],
                "location": r[3],
                "client": r[4],
                "status": r[5],
                "builtin": False,
                "created_at": r[6],
                "summary": json.loads(r[7]),
            })
    finally:
        con.close()
    return out


def ingest_uploaded_project(
    name: str,
    order_code: str,
    location: str,
    client: str,
    uploaded_files: list[tuple[str, bytes]],
) -> dict:
    if not name.strip():
        raise ValueError("Project name is required.")
    if not uploaded_files:
        raise ValueError("Attach at least one DWG, PDF, XLSX, or ZIP file.")

    pid = _slugify(name)
    proj_dir = config.CACHE_DIR / "projects" / pid / "raw"
    proj_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[tuple[Path, str]] = []
    for fname, raw_bytes in uploaded_files:
        safe_name = Path(fname).name
        dest = proj_dir / safe_name
        dest.write_bytes(raw_bytes)
        if safe_name.lower().endswith(".zip"):
            extract_dir = proj_dir / safe_name[:-4]
            extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(dest, "r") as zf:
                    for info in zf.infolist():
                        parts = _safe_zip_parts(info.filename)
                        if not parts:
                            continue
                        target = extract_dir.joinpath(*parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info, "r") as src, target.open("wb") as out:
                            shutil.copyfileobj(src, out)
                        saved_paths.append((target, target.relative_to(proj_dir).as_posix()))
                continue
            except zipfile.BadZipFile:
                pass
        saved_paths.append((dest, safe_name))

    manifest = [_inspect_file(p, rel) for p, rel in saved_paths]
    dwg_n = sum(1 for m in manifest if m["kind"] in ("dwg", "dxf"))
    pdf_n = sum(1 for m in manifest if m["kind"] == "pdf")
    scan_n = sum(1 for m in manifest if m["kind"] == "scan")
    boq_files = [m for m in manifest if m["kind"] == "boq_xlsx"]
    boq_rows = sum(int(m.get("rows") or 0) for m in boq_files)
    ignored_n = sum(1 for m in manifest if m["kind"] == "ignored")

    oda_ok = config.ODA_EXE.exists()
    summary = {
        "dwg_count": dwg_n,
        "pdf_count": pdf_n,
        "scan_count": scan_n,
        "boq_lines": boq_rows,
        "ignored_count": ignored_n,
        "contract_azn": None,
        "backed_lines": 0,
        "contradictions": 0,
        "backed_pct": 0.0,
        "oda_available": oda_ok,
        "stages": [
            {"step": "Package Ingest & SHA-256", "state": "done",
             "note": f"{len(manifest) - ignored_n} active files hashed ({ignored_n} junk ignored)"},
            {"step": "Format & Layer Classification", "state": "done",
             "note": f"{dwg_n} CAD, {pdf_n} vector PDF, {scan_n} scan, {len(boq_files)} BOQ sheet"},
            {"step": "ODA DWG-to-DXF Conversion", "state": "ready" if (dwg_n and oda_ok) else ("skipped" if not dwg_n else "queued"),
             "note": "ODA Converter detected & ready" if oda_ok else "Awaiting ODA Converter binary on host"},
            {"step": "Takeoff & BOQ Reconciliation", "state": "ready" if boq_files else "blocked",
             "note": f"Ready to reconcile {boq_rows} spreadsheet rows" if boq_files else "Attach a client .xlsx BOQ to run reconciliation"},
        ],
        "files": manifest[:120],
    }

    now = time.time()
    con = _connect()
    try:
        con.execute(
            "insert into project_package (id, name, order_code, location, client, status, created_at, summary_json) "
            "values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pid,
                name.strip(),
                order_code.strip() or "Unnumbered",
                location.strip() or "Azerbaijan",
                client.strip() or "Client Package",
                "ingested",
                now,
                json.dumps(summary, ensure_ascii=False),
            ),
        )
        con.commit()
    finally:
        con.close()

    return {
        "id": pid,
        "name": name.strip(),
        "order_code": order_code.strip() or "Unnumbered",
        "location": location.strip() or "Azerbaijan",
        "client": client.strip() or "Client Package",
        "status": "ingested",
        "builtin": False,
        "created_at": now,
        "summary": summary,
    }


def delete_project(project_id: str) -> bool:
    if project_id == "hadrut-9335":
        raise ValueError("The baseline Hadrut Order 9335 package cannot be deleted.")
    if not _PROJECT_ID.fullmatch(project_id or ""):
        raise ValueError("Unknown project.")
    con = _connect()
    try:
        cur = con.execute("delete from project_package where id = ?", (project_id,))
        con.commit()
        removed = cur.rowcount > 0
    finally:
        con.close()
    raw_dir = config.CACHE_DIR / "projects" / project_id
    if raw_dir.exists():
        shutil.rmtree(raw_dir, ignore_errors=True)
    return removed
