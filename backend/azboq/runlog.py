"""Structured run log. A warning is also a review item, never only a log line."""
import json
import platform
import subprocess
import sys
import time
from contextlib import contextmanager

from . import ENGINE_VERSION, config

_events: list[dict] = []
_review: list[dict] = []


def event(stage: str, kind: str, message: str, **data):
    row = {"t": round(time.time(), 3), "stage": stage, "kind": kind, "message": message, **data}
    _events.append(row)
    if kind in ("warning", "error"):
        _review.append({"stage": stage, "severity": kind, "message": message, **data})
    line = f"[{stage}] {kind}: {message}"
    print(line.encode(sys.stdout.encoding or "utf-8", "replace").decode(sys.stdout.encoding or "utf-8"), flush=True)


def warn(stage: str, message: str, **data):
    event(stage, "warning", message, **data)


@contextmanager
def stage(name: str):
    t0 = time.time()
    event(name, "start", "stage started")
    try:
        yield
    except Exception as exc:  # recorded, then re-raised
        event(name, "error", f"{type(exc).__name__}: {exc}")
        raise
    finally:
        event(name, "end", "stage finished", seconds=round(time.time() - t0, 2))


def review_items() -> list[dict]:
    return list(_review)


def events() -> list[dict]:
    return list(_events)


def reset():
    _events.clear()
    _review.clear()


def tool_versions() -> dict:
    out = {"python": platform.python_version(), "engine": ENGINE_VERSION}
    import ezdxf
    import openpyxl
    import pymupdf
    out["ezdxf"] = ezdxf.__version__
    out["openpyxl"] = openpyxl.__version__
    out["pymupdf"] = pymupdf.VersionBind
    out["oda"] = str(config.ODA_EXE) if config.ODA_EXE.exists() else "not installed"
    pkg = config.TOOLS_DIR / "libredwg" / "node_modules" / "@mlightcad" / "libredwg-web" / "package.json"
    if pkg.exists():
        out["libredwg_web"] = json.loads(pkg.read_text(encoding="utf-8")).get("version")
    try:
        out["node"] = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out["node"] = "not found"
    return out


def write_manifest(payload: dict):
    config.ensure_dirs()
    path = config.RUN_LOG_DIR / f"run-{time.strftime('%Y%m%d-%H%M%S')}.json"
    body = {"versions": tool_versions(), "events": _events, "review": _review, **payload}
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (config.RUN_LOG_DIR / "latest.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path
