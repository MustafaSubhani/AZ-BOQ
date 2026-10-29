import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
from azboq.ingest.register import build_register  # noqa: E402

reg = build_register()
print("total", reg["total"], reg["counts"])
print("duplicates", reg["duplicates"])
for f in reg["files"]:
    if f["kind"] != "junk":
        print(f"{f['kind']:22} {f.get('discipline',''):18} {f.get('building',''):14} {f['rel'][:90]}")
print(Counter((f.get("discipline")) for f in reg["files"]))
