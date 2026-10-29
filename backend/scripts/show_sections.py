import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq import store  # noqa: E402

bill = store.get("bill")
want = sys.argv[1:] or ["1.1", "3.5", "4.12", "10.1", "14.5", "18.1", "19.1", "20.1", "21.1", "22.1", "23.1"]
for code in want:
    s = next(x for x in bill["sections"] if x["code"] == code)
    print(f"== {code} {s['title'][:80]} [{s['building']}/{s['trade']}]")
    for l in bill["lines"]:
        if l["section"] == code:
            print(f"   {l['id']:9} {l['qty']!s:>10} {l['unit']:5} {l['description'][:100]}")
