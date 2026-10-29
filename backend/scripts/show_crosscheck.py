import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq.dwg.crosscheck import load_crosscheck  # noqa: E402

rows = load_crosscheck()
for r in sorted(rows.values(), key=lambda r: (r.get("agree", False), r["file"])):
    print(f"{'agree' if r.get('agree') else 'DIFF ':5} oda={r.get('oda_total')!s:>7} libre={r.get('libredwg_total')!s:>7} "
          f"lib={r.get('libredwg_status')!s:12} {r['file'][:60]}")
    for d in (r.get("layer_diffs") or [])[:4]:
        print("      layer", d)
