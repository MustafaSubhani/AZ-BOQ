"""Every number the engine uses or produces is a Value with its sources.

A missing input is BLOCKED with value None. Arithmetic on a blocked value never
coerces; it yields another blocked value that names what is missing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Method(str, Enum):
    SCHEDULE = "schedule"
    STATED = "stated"
    GEOMETRY = "geometry"
    DERIVED = "derived"
    VISION = "vision"
    RULE = "rule"
    MANUAL = "manual"


class Status(str, Enum):
    VERIFIED = "verified"
    EXTRACTED = "extracted"
    REVIEW = "review"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Source:
    file_id: str
    file_name: str
    locator: dict
    raw_text: str | None = None
    decoded_text: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Value:
    value: float | None
    unit: str
    method: Method
    status: Status
    sources: tuple[Source, ...] = ()
    formula: str | None = None
    inputs: dict[str, "Value"] = field(default_factory=dict)
    searched: tuple[str, ...] = ()
    rejected: tuple[dict, ...] = ()
    conflicts: tuple[dict, ...] = ()
    missing: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self):
        if self.status == Status.BLOCKED and self.value is not None:
            raise ValueError("a blocked value cannot carry a number")
        if self.status != Status.BLOCKED and self.value is None:
            raise ValueError("a value without a number must be BLOCKED")
        if self.status != Status.BLOCKED and not self.sources and self.method != Method.DERIVED:
            raise ValueError("a value needs at least one source")

    @property
    def blocked(self) -> bool:
        return self.status == Status.BLOCKED

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "method": self.method.value,
            "status": self.status.value,
            "sources": [s.to_dict() for s in self.sources],
            "formula": self.formula,
            "inputs": {k: v.to_dict() for k, v in self.inputs.items()},
            "searched": list(self.searched),
            "rejected": list(self.rejected),
            "conflicts": list(self.conflicts),
            "missing": list(self.missing),
            "note": self.note,
        }

    @staticmethod
    def from_dict(d: dict) -> "Value":
        return Value(
            value=d["value"],
            unit=d["unit"],
            method=Method(d["method"]),
            status=Status(d["status"]),
            sources=tuple(Source(**s) for s in d.get("sources", [])),
            formula=d.get("formula"),
            inputs={k: Value.from_dict(v) for k, v in d.get("inputs", {}).items()},
            searched=tuple(d.get("searched", [])),
            rejected=tuple(d.get("rejected", [])),
            conflicts=tuple(d.get("conflicts", [])),
            missing=tuple(d.get("missing", [])),
            note=d.get("note", ""),
        )


def blocked(unit: str, missing: list[str] | tuple[str, ...], searched: list[str] | tuple[str, ...], note: str = "",
            method: Method = Method.DERIVED) -> Value:
    return Value(None, unit, method, Status.BLOCKED, searched=tuple(searched), missing=tuple(missing), note=note)


def derive(unit: str, formula: str, fn, **inputs: Value) -> Value:
    """Combine inputs with fn. Any blocked input blocks the result and is named."""
    missing = [name for name, v in inputs.items() if v.blocked]
    if missing:
        return Value(None, unit, Method.DERIVED, Status.BLOCKED, formula=formula, inputs=dict(inputs),
                     missing=tuple(missing))
    result = fn(**{k: v.value for k, v in inputs.items()})
    worst = Status.EXTRACTED
    if any(v.status == Status.REVIEW for v in inputs.values()):
        worst = Status.REVIEW
    elif all(v.status == Status.VERIFIED for v in inputs.values()):
        worst = Status.VERIFIED
    return Value(float(result), unit, Method.DERIVED, worst, formula=formula, inputs=dict(inputs))


def iter_sources(v: Value):
    """All sources in the input tree, depth first."""
    yield from v.sources
    for child in v.inputs.values():
        yield from iter_sources(child)


def jsonable(obj: Any):
    if isinstance(obj, Value):
        return obj.to_dict()
    if isinstance(obj, Source):
        return obj.to_dict()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(type(obj).__name__)
