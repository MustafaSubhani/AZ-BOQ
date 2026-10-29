import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
from azboq import store  # noqa: E402
from azboq.dwg.read import load_dump  # noqa: E402
from azboq.text.normalise import fold_key  # noqa: E402

reg = store.get("register")


def dump_for(part):
    f = next(f for f in reg["files"] if part.lower() in f["rel"].lower() and f["kind"] == "drawing_cad")
    return load_dump(f["sha256"])


def rows_near(d, pattern, dx=40000, dy=8000, limit=2, max_lines=30):
    anchors = [t for t in d["texts"] if re.search(pattern, fold_key(t["text"]))]
    print(f"### {d['file'][-50:]} /{pattern}/ anchors={len(anchors)}")
    for a in anchors[:limit]:
        ax, ay, h = a["at"][0], a["at"][1], max(a["h"], 1)
        near = [t for t in d["texts"] if ax - dx * 0.2 <= t["at"][0] <= ax + dx and ay - dy <= t["at"][1] <= ay + h * 3]
        near.sort(key=lambda t: (-round(t["at"][1] / (h * 1.5)), t["at"][0]))
        print(f"--- {a['text'][:70]!r} at {a['at']} h={a['h']}")
        line, last, n = [], None, 0
        for t in near:
            k = round(t["at"][1] / (h * 1.5))
            if last is not None and k != last:
                print("    ", " | ".join(line)[:200])
                line = []
                n += 1
                if n > max_lines:
                    break
            line.append(t["text"].replace("\n", " ")[:40])
            last = k
        if line:
            print("    ", " | ".join(line)[:200])


naz = dump_for("NƏZARƏT")
rows_near(naz, r"metal kiremit", dx=30000, dy=12000, limit=3)
rows_near(naz, r"cardaq elementlerinin tesnifati|catilarin plani", dx=30000, dy=15000, limit=2)
son = dump_for("(SON)")
rows_near(son, r"tustu xeberverici", dx=40000, dy=4000, limit=1)
rows_near(son, r"kesim 1-1", dx=40000, dy=15000, limit=2, max_lines=20)
tank = dump_for("yangin su anbari dk")
rows_near(tank, r"material serfi|beton", dx=40000, dy=10000, limit=3)
vert = dump_for("Vertikalka")
rows_near(vert, r"torpaq kutlesinin balansi", dx=150, dy=90, limit=1)
