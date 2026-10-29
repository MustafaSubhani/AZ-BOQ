import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
from azboq import config, store  # noqa: E402

idx = json.loads((config.CACHE_DIR / "number-index.json").read_text(encoding="utf-8"))
sheets = store.get("sheets")
for sha, v in sheets["dwg"].items():
    regs = v["regions"]
    print(f"{v['file'][-55:]:55} regions={len(regs)} buildings={dict(Counter(r['building'] for r in regs))}")
print()
for val in [45200.0, 34600.0, 2700.0, 3300.0, 1395.8, 1360.8, 1360.2, 1414.2, 1660.0, 1992.0, 9.6, 0.23, 7625.4, 12996.0,
            8683.0, 4835.0, 1021.0, 1437.8, 383.7, 216.0, 599.7, 65.2, 127.14, 790.8, 1344.0, 665.3, 538.4]:
    hits = [e for e in idx if abs(e["value"] - val) < 1e-6]
    print(f"== {val}: {len(hits)} hits")
    for e in hits[:6]:
        print("   ", e["kind"], e.get("building"), e.get("sheet"), e["file"][-40:], "|", e.get("unit"), "|", e["context"][:90])
