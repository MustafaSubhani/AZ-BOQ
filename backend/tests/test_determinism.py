"""Same inputs, same outputs: the check must not depend on dict order, timing or randomness."""
import json

import pytest

from azboq import store


def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, default=str)


@pytest.mark.skipif(store.get("bill") is None, reason="pipeline has not run")
def test_bill_parse_is_deterministic():
    from azboq.bill.parse import parse_bill
    assert _canon(parse_bill()) == _canon(parse_bill())


@pytest.mark.skipif(store.get("takeoff") is None, reason="pipeline has not run")
def test_takeoff_is_deterministic():
    from azboq.engine.run import run_takeoff
    a, b = run_takeoff(), run_takeoff()
    assert _canon(a["items"]) == _canon(b["items"])
    assert _canon(a["items"]) == _canon(store.get("takeoff")["items"])
