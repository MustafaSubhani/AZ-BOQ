"""Command line: python -m azboq <command>."""
import argparse
import os
import sys


def _utf8():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _utf8()
    p = argparse.ArgumentParser(prog="azboq")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run every stage")
    run.add_argument("--only", nargs="*", help="stage names to run")
    sub.add_parser("convert", help="convert every DWG to DXF with ODA, offline")
    sub.add_parser("libredwg-check", help="second reader cross-check")
    sub.add_parser("fonts", help="build legacy font tables from embedded PDF fonts")
    sub.add_parser("hardcoded-report", help="write HARDCODED.md from demo_rules")
    tiles = sub.add_parser("tiles", help="pre-render every sheet region for the viewer")
    tiles.add_argument("--fresh", action="store_true", help="delete existing tiles first")
    ex = sub.add_parser("export", help="write the Excel and PDF exports")
    ex.add_argument("--no-excel", action="store_true", help="skip Excel automation")
    tr = sub.add_parser("translate", help="pre-warm the translation cache with OpenAI")
    tr.add_argument("--limit", type=int)
    serve = sub.add_parser("serve", help="start the API")
    serve.add_argument("--port", type=int, default=8780)
    args = p.parse_args(argv)

    if args.cmd == "run":
        from .pipeline import run_all
        run_all(only=args.only)
    elif args.cmd == "convert":
        from .dwg.oda import convert_all
        convert_all()
    elif args.cmd == "libredwg-check":
        from .dwg.crosscheck import run_crosscheck
        run_crosscheck()
    elif args.cmd == "fonts":
        from .text.build_tables import build_all
        build_all()
    elif args.cmd == "hardcoded-report":
        from .rules import write_hardcoded_report
        print(write_hardcoded_report())
    elif args.cmd == "tiles":
        import json
        import time
        from . import config, store
        from .dwg.oda import dxf_path_for
        from .dwg.render import render_all
        if args.fresh:
            for f in config.TILES_DIR.glob("*.png"):
                f.unlink()
        t0 = time.time()
        res = render_all(store.get("sheets"), dxf_path_for, lambda m: print(m, flush=True))
        res["seconds"] = round(time.time() - t0, 1)
        (config.TILES_DIR / "tiles.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"rendered {res['rendered']}, failed {len(res['failed'])}, {res['seconds']} s")
    elif args.cmd == "export":
        from .export.run import export_all
        export_all(use_excel=not args.no_excel)
    elif args.cmd == "translate":
        from .text.translate import prewarm
        prewarm(limit=args.limit)
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("azboq.api.app:app", host="127.0.0.1", port=args.port, reload=False)
    return 0
