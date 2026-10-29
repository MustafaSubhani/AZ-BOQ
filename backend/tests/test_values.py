import pytest

from azboq.values import Method, Source, Status, Value, blocked, derive

SRC = Source("abc", "f.dwg", {"kind": "dxf_entity", "handle": "1A"}, "2700", "2700")


def test_blocked_cannot_hold_number():
    with pytest.raises(ValueError):
        Value(3.0, "m", Method.RULE, Status.BLOCKED)


def test_number_needs_source():
    with pytest.raises(ValueError):
        Value(3.0, "m", Method.GEOMETRY, Status.EXTRACTED)


def test_blocked_input_blocks_result_and_names_it():
    length = Value(45.2, "m", Method.GEOMETRY, Status.EXTRACTED, sources=(SRC,))
    height = blocked("m", ["storey height"], ["section 1-1 dimension text"])
    area = derive("m2", "length * height", lambda length, height: length * height, length=length, height=height)
    assert area.blocked and area.value is None and area.missing == ("height",)


def test_derive_computes_with_sources():
    a = Value(2.0, "m", Method.STATED, Status.EXTRACTED, sources=(SRC,))
    b = Value(3.0, "m", Method.STATED, Status.EXTRACTED, sources=(SRC,))
    v = derive("m2", "a * b", lambda a, b: a * b, a=a, b=b)
    assert v.value == 6.0 and v.status == Status.EXTRACTED
    assert Value.from_dict(v.to_dict()).value == 6.0
