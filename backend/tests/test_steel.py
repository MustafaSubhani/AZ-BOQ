"""Steel kilograms stay on the mark they were printed for."""
from azboq import store
from azboq.match.steel import steel_families


def test_steel_families_are_blocked_without_a_plan_count():
    rows = steel_families(store.get("register") or {"files": []}, store.get("bill"))
    columns = next(row for row in rows if row["id"] == "columns")
    assert columns["status"] == "blocked"
    assert columns["marks"] > 0
    assert "sum_t" not in columns
    assert all(row["status"] == "blocked" for row in rows)
    sample = columns["tables"][0]
    assert sample["total_kg"] is not None
