import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
here = os.path.join(os.path.dirname(__file__), "..", "azboq", "text", "legacy_fonts")
for p in sorted(glob.glob(os.path.join(here, "*.json"))):
    t = json.load(open(p, encoding="utf8"))
    cells = [f"{k}{v['to']}{'' if v['score'] >= 0.6 else '?'}" for k, v in t.items()]
    print(os.path.basename(p), " ".join(cells))
