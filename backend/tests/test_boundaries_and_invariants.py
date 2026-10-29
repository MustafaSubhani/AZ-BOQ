"""The takeoff never sees the bill, every result has a source or a reason, and exports keep the client's style."""
import ast
import re
from pathlib import Path

import pytest

from azboq import config, store

ENGINE = Path(__file__).resolve().parents[1] / "azboq" / "engine"


def test_takeoff_cannot_read_the_bill():
    bad = []
    for path in ENGINE.rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "bill" in node.module:
                bad.append(f"{path.name}: imports {node.module}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in ("bill", "report"):
                bad.append(f"{path.name}: reads store '{node.value}'")
        if "BOQ-Hadrut" in src or "BILL_PATH" in src:
            bad.append(f"{path.name}: touches the bill file")
    assert not bad, bad


def test_platform_ui_never_mentions_hardcoding():
    src = Path(__file__).resolve().parents[2] / "frontend" / "src"
    bad = [f"{p.name}: {m.group(0)}" for p in src.rglob("*.ts*")
           for m in re.finditer(r"(?i)hardcod\w*|demo rule|HARDCODED\.md", p.read_text(encoding="utf-8"))]
    assert not bad, bad


needs_run = pytest.mark.skipif(store.get("report") is None, reason="pipeline has not run")


@needs_run
def test_every_bill_line_has_one_status_and_a_reason():
    bill, report = store.get("bill"), store.get("report")
    assert set(report["lines"]) == {l["id"] for l in bill["lines"]}
    allowed = {"matched", "different", "blocked", "printed", "derived", "review", "not_found"}
    for lid, r in report["lines"].items():
        assert r["status"] in allowed, lid
        assert r.get("reason"), lid


@needs_run
def test_values_have_sources_and_blocked_values_have_no_number():
    take = store.get("takeoff")
    for i in take["items"]:
        v = i["value"]
        if v["status"] == "blocked":
            assert v["value"] is None and (v["missing"] or v["note"]), i["id"]
        elif v["method"] != "derived":
            assert v["sources"], i["id"]


@needs_run
def test_depot_gate_passes():
    gate = store.get("takeoff")["gate"]
    assert gate["pass"], gate


@needs_run
def test_rules_all_cited():
    from azboq.rules import validate
    assert validate() == []


@pytest.mark.skipif(not (config.EXPORT_DIR / "BOQ-Hadrut-checked.xlsx").exists(), reason="exports not written")
def test_filled_bill_keeps_every_cell_style():
    from azboq.export.fidelity import compare_styles
    res = compare_styles(config.BILL_PATH, config.EXPORT_DIR / "BOQ-Hadrut-checked.xlsx")
    assert res["cell_style_diffs"] == 0, res["examples"]
