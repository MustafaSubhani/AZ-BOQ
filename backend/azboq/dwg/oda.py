"""Offline DWG to DXF conversion with the ODA File Converter.

The converter takes folders, not files, and its exit code is not trusted: a DXF
counts as converted only if it exists, is not empty and opens in ezdxf.
File names here contain ə, ³, double spaces and trailing dots, so every file is
staged under its hash in an ASCII folder of its own.
"""
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import ezdxf
from ezdxf import recover

from .. import config, runlog
from ..hashing import sha256

MANIFEST = "conversion-manifest.json"


def dxf_path_for(file_sha: str) -> Path:
    return config.DXF_DIR / f"{file_sha[:12]}.dxf"


def load_manifest() -> dict:
    p = config.DXF_DIR / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _open_check(path: Path) -> dict:
    try:
        doc = ezdxf.readfile(path)
        auditor_errors = 0
        mode = "readfile"
    except ezdxf.DXFStructureError:
        doc, auditor = recover.readfile(path)
        auditor_errors = len(auditor.errors)
        mode = "recover"
    msp = doc.modelspace()
    return {"open_mode": mode, "auditor_errors": auditor_errors, "modelspace_entities": len(msp),
            "insunits": doc.header.get("$INSUNITS", None), "acadver": doc.dxfversion}


def convert_one(src: Path, timeout: int = 600) -> dict:
    file_sha = sha256(src)
    out = dxf_path_for(file_sha)
    row = {"source": str(src), "sha256": file_sha, "dxf": str(out), "converter": str(config.ODA_EXE)}
    if out.exists() and out.stat().st_size > 0:
        row.update(_open_check(out))
        row["status"] = "cached"
        return row
    with tempfile.TemporaryDirectory(prefix="azboq-oda-") as tmp:
        tin, tout = Path(tmp, "in"), Path(tmp, "out")
        tin.mkdir()
        tout.mkdir()
        staged = tin / f"{file_sha[:12]}.dwg"
        shutil.copy2(src, staged)
        t0 = time.time()
        try:
            proc = subprocess.run(
                [str(config.ODA_EXE), str(tin), str(tout), "ACAD2018", "DXF", "0", "1", staged.name],
                capture_output=True, timeout=timeout,
            )
            row["exit_code"] = proc.returncode
        except subprocess.TimeoutExpired:
            row.update(status="failed", reason=f"timeout after {timeout} s")
            return row
        row["seconds"] = round(time.time() - t0, 1)
        produced = tout / f"{file_sha[:12]}.dxf"
        if not produced.exists() or produced.stat().st_size == 0:
            row.update(status="failed", reason="converter wrote no DXF (exit code is not trusted)")
            return row
        config.DXF_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), out)
    try:
        row.update(_open_check(out))
    except Exception as exc:  # the DXF exists but does not open
        row.update(status="failed", reason=f"DXF does not open: {type(exc).__name__}: {exc}")
        return row
    if row["modelspace_entities"] == 0:
        row.update(status="failed", reason="DXF opened with 0 model-space entities")
        return row
    row["status"] = "converted"
    return row


def convert_all() -> dict:
    if not config.ODA_EXE.exists():
        raise FileNotFoundError(f"ODA File Converter not found at {config.ODA_EXE}")
    config.ensure_dirs()
    manifest = load_manifest()
    dwgs = sorted(p for p in config.PACKAGE_DIR.rglob("*") if p.suffix.lower() == ".dwg")
    with runlog.stage("convert"):
        for src in dwgs:
            row = convert_one(src)
            manifest[row["sha256"]] = row
            if row["status"] == "failed":
                runlog.warn("convert", f"{src.name}: {row['reason']}", file=src.name)
            else:
                runlog.event("convert", "info", f"{src.name}: {row['status']}, {row['modelspace_entities']} entities")
            (config.DXF_DIR / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest
