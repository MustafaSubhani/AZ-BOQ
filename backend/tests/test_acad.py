"""Depot steel schedules kept as ACAD_TABLE cells."""
import json
from pathlib import Path

import pytest

from azboq.schedules.acad import acad_tables
from azboq.text.normalise import fold_key

DUMP = Path(r"D:\AZ-BOQ\cache\sheets\cd42f89a3f68.json")


def _cell(row, text, header_bit):
    return next(cell for cell in row["cells"] if cell["text"] == text and header_bit in fold_key(cell["header"]))


@pytest.mark.skipif(not DUMP.exists(), reason="depot drawing dump is not on this machine")
def test_column_s6_steel_totals_64_4_and_275_5():
    tables = acad_tables(json.loads(DUMP.read_text(encoding="utf-8")))
    table = next(t for t in tables if t["handle"] == "3998E7")
    assert "kq" in table["title"]
    row = next(row for row in table["rows"] if any(cell["text"] == "Sütun S-6" for cell in row["cells"]))
    bar = _cell(row, "64.4", "8")
    total = _cell(row, "275.5", "yekun")
    assert "240" in bar["header"]
    assert bar["unit"] == "kg"
    assert total["unit"] == "kg"
    assert _cell(row, "211.1", "cemi")["unit"] == "kg"


@pytest.mark.skipif(not DUMP.exists(), reason="depot drawing dump is not on this machine")
def test_column_s6_bar_schedule_keeps_length_count_and_mass():
    tables = acad_tables(json.loads(DUMP.read_text(encoding="utf-8")))
    table = next(t for t in tables if t["handle"] == "3996C5")
    row = next(row for row in table["rows"] if any(cell["text"] == "L=3650mm" for cell in row["cells"]))
    assert any(cell["text"] == "8" for cell in row["cells"])
    assert any(cell["text"] == "72.01" for cell in row["cells"])
    mass = next(cell for cell in row["cells"] if cell["text"] == "9.00")
    assert mass["unit"] == "kg"
    assert "kutle" in fold_key(mass["header"]) or "kq" in fold_key(mass["header"])
