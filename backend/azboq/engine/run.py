"""Run every extractor rule, attach conflicts, and flatten all inputs into the ledger."""
import re

from .. import rules as R
from .. import runlog
from ..text.normalise import fold_key
from ..values import Method, Source, Status, Value, iter_sources
from . import locate as L
from .extract import run_rule


def _rule_value(rule_id: str) -> Value:
    r = R.project_rule(rule_id)
    src = Source("rule", "demo_rules/project_rules.yaml", {"kind": "rule", "rule_id": rule_id, "citation": r["citation"]},
                 None, r.get("label_en"))
    return Value(float(r["value"]), r["unit"], Method.RULE, Status.EXTRACTED, sources=(src,), note=r["citation"])


def _ledger(item_id: str, path: str, v: Value, out: list):
    out.append({"item": item_id, "path": path, "value": v.value, "unit": v.unit, "method": v.method.value,
                "status": v.status.value, "sources": [s.to_dict() for s in v.sources][:3],
                "missing": list(v.missing), "searched": list(v.searched)[:6], "note": v.note,
                "conflicts": len(v.conflicts)})
    for name, child in v.inputs.items():
        _ledger(item_id, f"{path} › {name}", child, out)


def _project_conflicts() -> list[dict]:
    texts = []
    for sha in L.dwg_files():
        texts.extend((sha, t) for t in L.dump(sha)["texts"])
    out = []
    for c in R.load("conflicts"):
        sides = []
        for s in c["sides"]:
            needle = fold_key(s["search"])
            hits = []
            for sha, t in texts:
                if needle in fold_key(t["text"]):
                    hits.append({"file": L.files()[sha]["rel"], "file_id": sha, "handle": t["handle"],
                                 "text": t["text"][:160], "region": (L.region_of(sha, t["at"]) or {}).get("id")})
                    if len(hits) >= 3:
                        break
            sides.append({**s, "found_in_drawings": hits})
        out.append({**c, "sides": sides, "decided": False})
    return out


def run_takeoff() -> dict:
    items, done, ledger = [], {}, []
    rule_list = R.load("extractors")
    order = [r for r in rule_list if r["type"] != "derived"] + [r for r in rule_list if r["type"] == "derived"]
    with runlog.stage("takeoff"):
        for rule in order:
            v = run_rule(rule, done)
            if rule.get("conflict_rule") and not v.blocked:
                other = _rule_value(rule["conflict_rule"])
                if abs(other.value - v.value) > 1e-6:
                    conflict = {"value": other.value, "method": "rule", "citation": other.note,
                                "source": other.sources[0].to_dict()}
                    v = Value(v.value, v.unit, v.method, Status.REVIEW, sources=v.sources, formula=v.formula,
                              inputs=v.inputs, searched=v.searched, rejected=v.rejected,
                              conflicts=v.conflicts + (conflict,), note=(v.note + "; " if v.note else "") +
                              f"the general note gives {other.value:g}")
            done[rule["id"]] = v
            first = next(iter_sources(v), None)
            items.append({"id": rule["id"], "label_az": rule["label_az"], "label_en": rule["label_en"],
                          "building": rule["building"], "element": rule["element"], "unit": rule["unit"],
                          "billable": rule.get("billable", True),
                          "type": rule["type"], "citation": rule["citation"], "parent": bool(rule.get("parent")),
                          "value": v.to_dict(), "viewer": first.to_dict() if first else None})
            _ledger(rule["id"], rule["label_en"], v, ledger)
            if v.blocked:
                runlog.warn("takeoff", f"{rule['label_en']}: blocked ({v.note or 'missing ' + ', '.join(v.missing)})",
                            item=rule["id"])
            else:
                runlog.event("takeoff", "info", f"{rule['label_en']}: {v.value:g} {v.unit} [{v.method.value}, {v.status.value}]")
        gate = _gate(done)
        conflicts = _project_conflicts()
        for r in R.load("project_rules"):
            _ledger(r["id"], r["label_en"], _rule_value(r["id"]), ledger)
    rule_count = sum(1 for e in ledger if e["method"] == "rule")
    return {"items": items, "ledger": ledger, "gate": gate, "conflicts": conflicts, "rule_count": rule_count,
            "problems": R.validate()}


def _gate(done: dict) -> dict:
    checks = []
    for item, expect, tol in (("gate_long", 45.200, 0.050), ("gate_short", 34.600, 0.050), ("bay_module", 6.000, 0.020),
                              ("storey_basement", 2.70, 0.02), ("storey_upper", 3.30, 0.02)):
        v = done.get(item)
        got = None if v is None or v.blocked else v.value
        ok = got is not None and abs(got - expect) <= tol
        checks.append({"item": item, "expected": expect, "tolerance": tol, "got": got, "pass": ok})
    passed = all(c["pass"] for c in checks[:2])
    if not passed:
        runlog.warn("takeoff", "45.200 × 34.600 m gate failed: units or scale cannot be trusted for the depot")
    return {"pass": passed, "checks": checks}
