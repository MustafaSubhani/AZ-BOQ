"""Compare ODA (via ezdxf) and LibreDWG entity counts per layer and type.

Like is compared with like: top-level entities in model space and paper-space
layouts, without expanding blocks.
"""
import json
import subprocess
from collections import Counter
from pathlib import Path

import ezdxf

from .. import config, runlog
from ..hashing import sha256
from .oda import dxf_path_for, load_manifest

TOTAL_TOLERANCE = 0.02
LAYER_TOLERANCE = 0.05
LAYER_MIN = 10


def libredwg_counts(src: Path, file_sha: str, timeout: int = 180) -> dict:
    out = config.LIBREDWG_DIR / f"{file_sha[:12]}.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    config.LIBREDWG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["node", str(config.LIBREDWG_TOOL), str(src), str(out)], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        row = {"source": str(src), "status": "timeout"}
        out.write_text(json.dumps(row), encoding="utf-8")
        return row
    if not out.exists():
        row = {"source": str(src), "status": "process_died"}
        out.write_text(json.dumps(row), encoding="utf-8")
        return row
    return json.loads(out.read_text(encoding="utf-8"))


def ezdxf_counts(dxf: Path) -> Counter:
    doc = ezdxf.readfile(dxf)
    c = Counter()
    for layout in doc.layouts:
        for e in layout:
            c[(e.dxf.get("layer", ""), e.dxftype())] += 1
    return c


# LibreDWG and ezdxf name a few types differently.
TYPE_ALIASES = {"LWPOLYLINE": "LWPOLYLINE", "POLYLINE": "POLYLINE", "MULTILEADER": "MULTILEADER", "MLEADER": "MULTILEADER"}


def compare(oda: Counter, lib: dict) -> dict:
    lib_counts = Counter()
    for key, n in lib.get("counts", {}).items():
        layer, typ = key.split("\u0000")
        lib_counts[(layer, TYPE_ALIASES.get(typ, typ))] += n
    oda_norm = Counter()
    for (layer, typ), n in oda.items():
        oda_norm[(layer, TYPE_ALIASES.get(typ, typ))] += n
    oda_total, lib_total = sum(oda_norm.values()), sum(lib_counts.values())
    layer_diffs = []
    layers = {k[0] for k in oda_norm} | {k[0] for k in lib_counts}
    for layer in sorted(layers):
        a = sum(n for (l, _), n in oda_norm.items() if l == layer)
        b = sum(n for (l, _), n in lib_counts.items() if l == layer)
        big = max(a, b)
        if big >= LAYER_MIN and abs(a - b) / big > LAYER_TOLERANCE:
            layer_diffs.append({"layer": layer, "oda": a, "libredwg": b})
    type_diffs = []
    for typ in sorted({k[1] for k in oda_norm} | {k[1] for k in lib_counts}):
        a = sum(n for (_, t), n in oda_norm.items() if t == typ)
        b = sum(n for (_, t), n in lib_counts.items() if t == typ)
        big = max(a, b)
        if big >= LAYER_MIN and abs(a - b) / big > LAYER_TOLERANCE:
            type_diffs.append({"type": typ, "oda": a, "libredwg": b})
    total_diff = abs(oda_total - lib_total) / oda_total if oda_total else 1.0
    # LibreDWG names some layers differently ("0 @ 1" for ""), so layers only disagree
    # when the entity types do as well.
    agree = lib.get("status") == "ok" and total_diff <= TOTAL_TOLERANCE and not type_diffs
    naming_only = agree and bool(layer_diffs)
    return {"oda_total": oda_total, "libredwg_total": lib_total, "total_diff": round(total_diff, 4),
            "type_diffs": type_diffs[:30], "layer_diffs": layer_diffs[:40], "agree": agree,
            "layer_naming_differs": naming_only}


def run_crosscheck() -> dict:
    manifest = load_manifest()
    results = {}
    dwgs = sorted(p for p in config.PACKAGE_DIR.rglob("*") if p.suffix.lower() == ".dwg")
    with runlog.stage("crosscheck"):
        for src in dwgs:
            file_sha = sha256(src)
            conv = manifest.get(file_sha, {})
            lib = libredwg_counts(src, file_sha)
            row = {"file": src.name, "sha256": file_sha, "oda_status": conv.get("status", "not converted"),
                   "libredwg_status": lib.get("status"), "libredwg_error": lib.get("error")}
            dxf = dxf_path_for(file_sha)
            if conv.get("status") in ("converted", "cached") and dxf.exists():
                row.update(compare(ezdxf_counts(dxf), lib))
            else:
                row["agree"] = False
            if not row["agree"]:
                runlog.warn("crosscheck", f"{src.name}: readers disagree or one failed", file=src.name,
                            oda=row.get("oda_total"), libredwg=row.get("libredwg_total"),
                            libredwg_status=row["libredwg_status"])
            results[file_sha] = row
        (config.LIBREDWG_DIR / "crosscheck.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
    return results


def load_crosscheck() -> dict:
    p = config.LIBREDWG_DIR / "crosscheck.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
