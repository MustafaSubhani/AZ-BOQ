"""Print a trimmed sample of each stored stage, to see the shapes the frontend consumes."""
import json
import sys

from azboq import store

sys.stdout.reconfigure(encoding="utf-8")


def trim(x, depth=0):
    if isinstance(x, dict):
        return {k: trim(v, depth + 1) for k, v in list(x.items())[:14]}
    if isinstance(x, list):
        return [trim(v, depth + 1) for v in x[:2]] + ([f"... {len(x)} items"] if len(x) > 2 else [])
    if isinstance(x, str) and len(x) > 90:
        return x[:90] + "…"
    return x


for name in sys.argv[1:]:
    data = store.get(name)
    if name == "report":
        lines = data["lines"]
        sample = {}
        for lid, r in lines.items():
            sample.setdefault(r["status"], (lid, r))
        data = {**{k: v for k, v in data.items() if k != "lines"}, "lines_by_status": sample}
    print(f"===== {name}")
    print(json.dumps(trim(data), ensure_ascii=False, indent=1)[:6000])
