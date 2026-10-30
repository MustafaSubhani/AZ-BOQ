"""Readers keep what they cannot store visible, and they read tables, leaders and hatches."""
import ezdxf

from azboq.dwg.layers import fix_mojibake, role
from azboq.dwg.read import dump, mtext_bbox
from azboq.engine.locate import rows


def test_mojibake_layer_names_become_cyrillic_and_real_azeri_is_kept():
    fixed = fix_mojibake("àğìà 0.25")
    assert fixed != "àğìà 0.25"
    assert any("\u0400" <= ch <= "\u04FF" for ch in fixed)
    assert fix_mojibake("Ölçülər") == "Ölçülər"
    assert "Ø" not in "àğìà" or fix_mojibake("Ø20") == "Ø20"


def test_mtext_top_left_box_grows_downward():
    box, estimated = mtext_bbox((0, 10), attach=1, width=20, h=2, n_lines=1)
    assert estimated is False
    assert box[0] == 0 and box[2] == 20
    assert box[3] == 10 and box[1] < 10


def test_overlapping_mtext_boxes_are_one_row():
    high = {"at": [0, 10], "h": 2, "bbox": [0, 8, 10, 10], "bbox_estimated": False}
    low = {"at": [12, 8.2], "h": 2, "bbox": [12, 7.5, 20, 9.5], "bbox_estimated": False}
    apart = {"at": [0, 0], "h": 2, "bbox": [0, -2, 10, 0], "bbox_estimated": False}
    grouped = rows([high, apart, low])
    assert len(grouped) == 2
    assert {id(t) for t in grouped[0]} == {id(high), id(low)}


def test_unread_entity_types_are_counted(tmp_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text("Hello", dxfattribs={"insert": (0, 0), "height": 2.5})
    msp.add_point((1, 1))
    msp.add_line((0, 0), (10, 0))
    path = tmp_path / "one.dxf"
    doc.saveas(path)
    data, geom = dump(path)
    assert any(t["text"] == "Hello" for t in data["texts"])
    assert data["dropped_by_type"].get("POINT") == 1
    assert geom["lines"] == [[0.0, 0.0, 10.0, 0.0, "0"]]
    assert role("0") == "unclassified"
