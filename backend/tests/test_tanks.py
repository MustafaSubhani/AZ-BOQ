"""Tank material tables: the missed bottom row, and a wall count that is not assumed."""
from pathlib import Path

import pytest

from azboq.engine.tanks import read_tank

DUMP = Path(r"D:\AZ-BOQ\cache\sheets\5ed62808af32.json")


def _sha(fragment: str) -> str | None:
    from azboq import store
    from azboq.text.normalise import fold_key
    for f in (store.get("register") or {"files": []})["files"]:
        if f["kind"] == "drawing_cad" and fragment in fold_key(f["name"]):
            return f["sha256"]
    return None


@pytest.mark.skipif(not DUMP.exists(), reason="fire-tank drawing dump is not on this machine")
def test_fire_tank_reads_the_bottom_and_does_not_assume_four_walls():
    sha = _sha("yangin su anbari dk")
    assert sha
    data = read_tank(sha, "fire_tanks")
    assert data["rows"]["cover"]["value"] == pytest.approx(4.13)
    assert data["rows"]["bottom"]["value"] == pytest.approx(9.41)
    assert data["rows"]["wall"]["value"] == pytest.approx(4.58)
    assert data["rows"]["wall"]["per_element"] is True
    assert data["count"]["n"] == 4
    assert "Miq." in data["count_note"]
    assert abs(data["rows"]["bottom"]["value"] + data["count"]["n"] * data["rows"]["wall"]["value"] - 27.73) < 1e-9


@pytest.mark.skipif(not DUMP.exists(), reason="drinking-tank drawing dump is not on this machine")
def test_drinking_tank_walls_are_not_per_element():
    sha = _sha("icmeli su anbari dk")
    assert sha
    data = read_tank(sha, "drinking_tanks")
    assert data["rows"]["cover"]["value"] == pytest.approx(1.58)
    assert data["rows"]["bottom"]["value"] == pytest.approx(3.89)
    assert data["rows"]["wall"]["value"] == pytest.approx(10.60)
    assert data["rows"]["wall"]["per_element"] is False
    assert data["rows"]["bottom"]["value"] + data["rows"]["wall"]["value"] == pytest.approx(14.49)
