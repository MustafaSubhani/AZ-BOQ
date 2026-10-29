import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
from azboq.dwg.oda import load_manifest  # noqa: E402
from azboq.dwg.read import dump  # noqa: E402

needle = sys.argv[1]
man = load_manifest()
row = next(r for r in man.values() if needle.lower() in r["source"].lower())
t0 = time.time()
d = dump(row["dxf"])
print(row["source"], f"{time.time()-t0:.1f}s", "units", d["insunits"], "texts", len(d["texts"]), "dims", len(d["dims"]),
      "polys", len(d["polys"]), "lines", len(d["lines"]), "inserts", len(d["inserts"]))
print(Counter(t["scheme"] for t in d["texts"]))
print(Counter(l["role"] for l in d["layers"]))
for t in d["texts"][:: max(1, len(d["texts"]) // 40)][:40]:
    print(" ", t["scheme"][:4], t["layer"][:20], repr(t["text"][:90]), "| raw:" if t["scheme"] != "unicode" else "", t["raw"][:50] if t["scheme"] != "unicode" else "")
big = sorted([x for x in d["dims"] if x["measurement"]], key=lambda x: -x["measurement"])[:12]
for x in big:
    print("  dim", round(x["measurement"], 1), repr(x["text"]), x["layer"])
