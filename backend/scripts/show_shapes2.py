"""Second look at payload shapes: ledger, conversion, exports, coverage statuses, operations ids."""
import json
import sys
from collections import Counter

from azboq import config, store

sys.stdout.reconfigure(encoding="utf-8")
take = store.get("takeoff")
print("ledger type", type(take["ledger"]).__name__, len(take["ledger"]))
print(json.dumps(take["ledger"][:2] if isinstance(take["ledger"], list) else list(take["ledger"].items())[:2],
                 ensure_ascii=False, indent=1)[:2500])
print("problems", take.get("problems"))
print("value conflicts sample", [i["value"]["conflicts"] for i in take["items"] if i["value"]["conflicts"]][:1])
print("statuses", Counter(i["value"]["status"] for i in take["items"]), len(take["items"]))
conv = store.get("conversion")
print(json.dumps(conv["files"][0], ensure_ascii=False, indent=1)[:2000])
print("conv statuses", Counter(f["status"] for f in conv["files"]))
print("coverage statuses", Counter(c["status"] for c in store.get("source_map")["cells"]))
ops = store.get("operations")
print("registers", [(r["id"], len(r["rows"]), r["empty_note"][:60]) for r in ops["registers"]])
p = config.EXPORT_DIR / "exports.json"
print(p.read_text(encoding="utf-8")[:2500] if p.exists() else "no exports.json")
rep = store.get("report")
print("measured_no_bill_line", len(rep["measured_no_bill_line"]), "value_by_status", rep["value_by_status"])
ex = [r for r in rep["lines"].values() if r.get("reviewer")][:2]
print("reviewer", json.dumps(ex, ensure_ascii=False)[:800])
