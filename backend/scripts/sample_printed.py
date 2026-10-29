import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq import store  # noqa: E402

rep, bill = store.get("report"), store.get("bill")
by_id = {l["id"]: l for l in bill["lines"]}
printed = [k for k, v in rep["lines"].items() if v["status"] == "printed"]
random.seed(4)
for k in random.sample(printed, 30):
    l, r = by_id[k], rep["lines"][k]
    s = (r.get("sources") or [{}])[0]
    print(f"{k:9} {l['qty']:>10g} {l['unit']:4} | {l['description'][:55]:55} | ctx: {str(s.get('raw_text'))[:60]!r}")
print("different:", [(k, v["reason"]) for k, v in rep["lines"].items() if v["status"] == "different"])
