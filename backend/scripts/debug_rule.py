import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq.engine import locate as L  # noqa: E402
from azboq.text.normalise import fold_key  # noqa: E402

sha = L.dwg_files("XOCAVEND-NƏZARƏT")[0]
for r in L.regions(sha):
    print(r["id"], r["building"], (r["number"] or {}).get("raw"), r["title"][:40])
for t, r in L.texts_in(sha):
    if fold_key(t["text"]).startswith("cemi"):
        row = L.row_of(t, L.dump(sha)["texts"], tol=0.6, max_dx=(t.get("h") or 1) * 60)
        print("CEMI", repr(t["text"]), t["at"], t["h"], (r or {}).get("id"), (r or {}).get("building"), "| row:",
              [(o["text"][:20], round(o["at"][1] - t["at"][1], 1)) for o in row][:8])
