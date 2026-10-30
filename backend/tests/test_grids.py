"""Steel schedules drawn as text on ruling lines, not as an ACAD_TABLE."""
import json
from pathlib import Path

import pytest

from azboq.schedules.grids import grids_in_dump
from azboq.text.normalise import fold_key

DUMP = Path(r"D:\AZ-BOQ\cache\sheets\8556f20831a2.json")


def _line(x0, y0, x1, y1):
    return {"role": "table", "a": [x0, y0], "b": [x1, y1]}


def _frame():
    lines = []
    for x in (0, 100, 200, 300, 400):
        lines.append(_line(x, 0, x, 400))
    for y in (0, 100, 200, 300, 400):
        lines.append(_line(0, y, 400, y))
    texts = [
        {"at": [50, 350], "text": "Elementin markası"},
        {"at": [350, 350], "text": "Cəmi kq"},
        {"at": [250, 250], "text": "A240"},
        {"at": [150, 150], "text": "Ø 8"},
        {"at": [250, 150], "text": "Ø 10"},
        {"at": [50, 50], "text": "Mlb-1"},
        {"at": [150, 50], "text": "30.80"},
        {"at": [250, 50], "text": "12.00"},
        {"at": [350, 50], "text": "104.00"},
    ]
    return {"lines": lines, "texts": texts}


def test_a_class_header_covers_the_empty_columns_beside_it():
    tables = grids_in_dump(_frame())
    assert len(tables) == 1
    row = tables[0]["rows"][0]
    by_text = {cell["text"]: cell for cell in row["cells"]}
    assert "a240" in fold_key(by_text["30.80"]["header"])
    assert "8" in by_text["30.80"]["header"]
    assert by_text["30.80"]["unit"] == "kg"
    assert by_text["104.00"]["unit"] == "kg"
    assert "cemi" in fold_key(by_text["104.00"]["header"])


@pytest.mark.skipif(not DUMP.exists(), reason="guard-room drawing dump is not on this machine")
def test_guard_room_steel_grid_reads_the_mark_and_the_total():
    tables = grids_in_dump(json.loads(DUMP.read_text(encoding="utf-8")))
    steel = [t for t in tables if "serfi" in fold_key(t["title"]) or "polad" in fold_key(t["title"])]
    assert steel
    found = None
    for table in steel:
        for row in table["rows"]:
            texts = {cell["text"] for cell in row["cells"]}
            if "Mlb-1" in texts and "104.00" in texts:
                found = row
    assert found
    total = next(cell for cell in found["cells"] if cell["text"] == "104.00")
    bar = next(cell for cell in found["cells"] if cell["text"] == "30.80" and "8" in cell["header"])
    assert total["unit"] == "kg"
    assert "cemi" in fold_key(total["header"])
    assert bar["unit"] == "kg"
    assert "a240" in fold_key(bar["header"])
