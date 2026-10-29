import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq.engine import locate as L  # noqa: E402
from azboq.engine.extract import _anchor_match, _cell_number  # noqa: E402
from azboq.text.normalise import fold_key  # noqa: E402

for name, pat in (("yangin su anbari dk", r'^beton "?b25"?$'), ("(SON)", r"^tustu xeberverici$")):
    sha = L.dwg_files(name)[0]
    print("##", L.files()[sha]["rel"][-50:])
    for t, r in L.texts_in(sha):
        k = fold_key(t["text"])
        if "beton" in k or "tustu" in k:
            row = L.row_of(t, L.dump(sha)["texts"], tol=0.6, max_dx=(t.get("h") or 1) * 60)
            print(" ", repr(t["text"][:40]), "match" if _anchor_match(pat, t["text"]) else "-", (r or {}).get("id"),
                  (r or {}).get("building"), "| row:", [(o["text"][:16], _cell_number(o["text"])) for o in row][:7])
