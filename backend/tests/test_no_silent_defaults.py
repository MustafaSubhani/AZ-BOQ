"""Engine code may not invent numbers. These are the patterns that hid the Constech tank height."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "azboq"
SCAN = [ROOT / "engine", ROOT / "match", ROOT / "export"]
ALLOW = "# allow-default:"


def _is_number(node) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.operand, ast.Constant):
        return _is_number(node.operand)
    return False


def _violations(path: Path):
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    found = []

    def allowed(node) -> bool:
        line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
        return ALLOW in line

    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and any(_is_number(v) for v in node.values[1:]):
            if not allowed(node):
                found.append((node.lineno, "x or <number>"))
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name == "get" and len(node.args) >= 2 and _is_number(node.args[1]) and not allowed(node):
                found.append((node.lineno, ".get(k, <number>)"))
            if name == "getattr" and len(node.args) >= 3 and _is_number(node.args[2]) and not allowed(node):
                found.append((node.lineno, "getattr(o, n, <number>)"))
            if name in ("max", "min") and any(_is_number(a) for a in node.args) and not allowed(node):
                found.append((node.lineno, f"{name}(..., <number>) clamp"))
        if isinstance(node, ast.ExceptHandler):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and _is_number(sub.value) and not allowed(sub):
                    found.append((sub.lineno, "numeric assignment inside except"))
    return found


def test_engine_has_no_silent_defaults():
    problems = []
    for folder in SCAN:
        for path in sorted(folder.rglob("*.py")):
            for line, what in _violations(path):
                problems.append(f"{path.relative_to(ROOT)}:{line}: {what}")
    assert not problems, "silent defaults found:\n" + "\n".join(problems)


def test_detector_catches_the_constech_pattern(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("h = (levels.get('roof') or 0.0) - levels.get('ground', 0)\n", encoding="utf-8")
    kinds = {k for _, k in _violations(bad)}
    assert "x or <number>" in kinds and ".get(k, <number>)" in kinds
