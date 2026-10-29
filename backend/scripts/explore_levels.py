import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
from azboq.engine import locate as L  # noqa: E402
from azboq.text.normalise import fold_key  # noqa: E402

LEVEL = re.compile(r"^[±+\-]?\s?\d{1,2}[.,]\d{3}$")
for name in ["(SON)", "yangin deposu dk son"]:
    for sha in L.dwg_files(name):
        regs = L.regions(sha)
        print("##", L.files()[sha]["rel"][-45:], len(regs), "regions")
        for r in regs:
            if r["building"] != "depot":
                continue
            lv = Counter(t["text"].strip() for t, rr in L.texts_in(sha, "depot") if rr and rr["id"] == r["id"] and LEVEL.match(t["text"].strip()))
            cemi = [t for t, rr in L.texts_in(sha, "depot") if rr and rr["id"] == r["id"] and fold_key(t["text"].strip()) == "cemi"]
            print(f"  {r['id']:4} {str((r['number'] or {}).get('raw')):18} {r['title'][:45]!r:48} levels={dict(lv.most_common(8))} cemi={len(cemi)}")
for sha in L.pdf_files("9335 MH.pdf"):
    d = L.pdf(sha)
    for p in d["pages"]:
        lines = [l["text"] for l in p["lines"]]
        cemi = [i for i, t in enumerate(lines) if fold_key(t).startswith("cemi")]
        lv = [t for t in lines if LEVEL.match(t.strip())]
        print(f"pdf p{p['page']:2} {str((p.get('number') or {}).get('raw')):16} {p['title'][:40]!r:42} cemi={[lines[i:i+3] for i in cemi][:2]} levels={sorted(set(lv))[:8]}")
