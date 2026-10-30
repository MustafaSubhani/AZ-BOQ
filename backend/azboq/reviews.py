"""A person's decision, stored and applied after takeoff. It never measures, and it never edits the rules."""
import json
import re
import sqlite3
import time

from . import config
from .values import Method, Source, Status, Value

SCHEMA = """create table if not exists review (
    id integer primary key autoincrement,
    target_kind text not null,
    target_id text not null,
    action text not null,
    payload text not null,
    reason text not null check (length(trim(reason)) > 0),
    author text not null,
    created_at real not null,
    superseded_by integer references review(id)
)"""

_TOKEN = re.compile(r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*|×|÷|[+\-*/(),]")
_ACTIONS = {"override", "set_input", "accept", "reject", "map", "decide", "reset"}


class ExprError(ValueError):
    pass


def evaluate(expression: str, variables: dict | None = None) -> float:
    """Numbers, names, + − × ÷, parentheses, sum and round. No Python eval."""
    env = {k: float(v) for k, v in (variables or {}).items()}
    return _Parser(_tokens(expression), env).parse()


def manual_value(payload: dict, reason: str, author: str, review_id: int) -> Value:
    src = Source("manual", f"review #{review_id}",
                 {"kind": "manual", "review_id": review_id, "author": author}, None, reason)
    units = payload.get("units") or {}
    inputs = {}
    env = {}
    for name, raw in (payload.get("variables") or {}).items():
        if isinstance(raw, dict):
            item = Value.from_dict(raw)
        else:
            item = Value(float(raw), units.get(name, ""), Method.MANUAL, Status.REVIEW, sources=(src,))
        inputs[name] = item
        if item.value is None:
            raise ExprError(f"{name} has no number")
        env[name] = item.value
    result = evaluate(payload["expression"], env)
    return Value(float(result), payload["unit"], Method.MANUAL, Status.REVIEW, sources=(src,),
                 formula=payload["expression"], inputs=inputs, note=f"{author}: {reason}")


def add_review(target_kind: str, target_id: str, action: str, payload: dict, reason: str, author: str,
               db=None) -> int:
    if action not in _ACTIONS:
        raise ExprError(f"unknown action {action}")
    if not (reason or "").strip() or not (author or "").strip():
        raise ExprError("a review needs an author and a reason")
    if action == "override":
        try:
            evaluate(payload.get("expression") or "", {name: 1 for name in (payload.get("variables") or {})})
        except ExprError as exc:
            if str(exc) != "division by zero":
                raise
    with _connect(db) as con:
        cur = con.execute(
            "insert into review (target_kind, target_id, action, payload, reason, author, created_at) "
            "values (?, ?, ?, ?, ?, ?, ?)",
            (target_kind, target_id, action, json.dumps(payload, ensure_ascii=False), reason.strip(), author.strip(),
             time.time()),
        )
        new_id = int(cur.lastrowid)
        con.execute(
            "update review set superseded_by = ? where target_kind = ? and target_id = ? and id != ? "
            "and superseded_by is null",
            (new_id, target_kind, target_id, new_id),
        )
    return new_id


def supersede(review_id: int, author: str, reason: str, db=None) -> int:
    """Mark a review finished. The row stays. A reset row is what replaces it."""
    row = get_review(review_id, db)
    if row is None or row["superseded_by"] is not None:
        raise ExprError("that review is not active")
    return add_review(row["target_kind"], row["target_id"], "reset", {}, reason, author, db)


def active_reviews(db=None) -> list[dict]:
    with _connect(db) as con:
        rows = con.execute(
            "select id, target_kind, target_id, action, payload, reason, author, created_at "
            "from review where superseded_by is null and action != 'reset' order by id"
        ).fetchall()
    return [_row(r) for r in rows]


def get_review(review_id: int, db=None) -> dict | None:
    with _connect(db) as con:
        row = con.execute(
            "select id, target_kind, target_id, action, payload, reason, author, created_at, superseded_by "
            "from review where id = ?",
            (review_id,),
        ).fetchone()
    if row is None:
        return None
    item = _row(row[:8])
    item["superseded_by"] = row[8]
    return item


def apply_reviews(takeoff: dict, reviews: list[dict] | None = None, db=None) -> dict:
    """Replace takeoff items a person overrode. Other actions are recorded and not measured."""
    reviews = active_reviews(db) if reviews is None else reviews
    if not reviews:
        return takeoff
    items = {item["id"]: json.loads(json.dumps(item)) for item in takeoff.get("items") or []}
    applied = []
    for review in reviews:
        if review["action"] == "override" and review["target_kind"] == "item":
            item = items.get(review["target_id"])
            if item is None:
                continue
            payload = review["payload"] if isinstance(review["payload"], dict) else json.loads(review["payload"])
            value = manual_value(payload, review["reason"], review["author"], review["id"])
            item["value"] = value.to_dict()
            item["review_id"] = review["id"]
            applied.append(review["id"])
        elif review["action"] == "set_input" and review["target_kind"] == "item":
            item = items.get(review["target_id"])
            if item is None:
                continue
            payload = review["payload"] if isinstance(review["payload"], dict) else json.loads(review["payload"])
            if _set_input(item, payload, review):
                applied.append(review["id"])
    order = [item["id"] for item in takeoff.get("items") or []]
    return {**takeoff, "items": [items[i] for i in order if i in items], "review_ids": applied}


def _set_input(item: dict, payload: dict, review: dict) -> bool:
    """Set one named input and recompute the formula. A missing name does nothing."""
    name = payload.get("name")
    if not name or payload.get("value") is None:
        return False
    value = item["value"]
    inputs = value.setdefault("inputs", {})
    src = Source("manual", f"review #{review['id']}",
                 {"kind": "manual", "review_id": review["id"], "author": review["author"]}, None, review["reason"])
    inputs[name] = Value(float(payload["value"]), payload.get("unit") or "", Method.MANUAL, Status.REVIEW,
                         sources=(src,), note=f"{review['author']}: {review['reason']}").to_dict()
    formula = value.get("formula")
    if not formula:
        return True
    env = {}
    for key, child in inputs.items():
        if child.get("value") is None:
            return True
        env[key] = child["value"]
    value["value"] = float(evaluate(formula, env))
    value["method"] = "manual"
    value["status"] = "review"
    value["note"] = f"{review['author']}: {review['reason']}"
    item["review_id"] = review["id"]
    return True


def apply_to_takeoff() -> list[int]:
    """Write the reviewed takeoff only when a review changes an item."""
    from . import store
    reviews = active_reviews()
    if not reviews:
        return []
    takeoff = store.get("takeoff")
    if takeoff is None:
        return []
    reviewed = apply_reviews(takeoff, reviews)
    store.put("takeoff", reviewed)
    return reviewed.get("review_ids") or []


def _tokens(expression: str) -> list[str]:
    tokens = []
    i = 0
    while i < len(expression):
        if expression[i].isspace():
            i += 1
            continue
        match = _TOKEN.match(expression, i)
        if not match:
            raise ExprError(f"cannot read '{expression[i:]}'")
        tokens.append(match.group(0))
        i = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[str], env: dict):
        self.tokens = tokens
        self.env = env
        self.i = 0

    def parse(self) -> float:
        if not self.tokens:
            raise ExprError("the expression is empty")
        value = self._expr()
        if self._peek() is not None:
            raise ExprError(f"unexpected '{self._peek()}'")
        return float(value)

    def _peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _eat(self, expected=None):
        token = self._peek()
        if token is None or (expected is not None and token != expected):
            raise ExprError(f"expected {expected or 'a value'}")
        self.i += 1
        return token

    def _expr(self) -> float:
        value = self._term()
        while self._peek() in ("+", "-"):
            op = self._eat()
            right = self._term()
            value = value + right if op == "+" else value - right
        return value

    def _term(self) -> float:
        value = self._factor()
        while self._peek() in ("*", "/", "×", "÷"):
            op = self._eat()
            right = self._factor()
            if op in ("/", "÷"):
                if right == 0:
                    raise ExprError("division by zero")
                value = value / right
            else:
                value = value * right
        return value

    def _factor(self) -> float:
        token = self._peek()
        if token == "-":
            self._eat()
            return -self._factor()
        if token == "(":
            self._eat()
            value = self._expr()
            self._eat(")")
            return value
        if token in ("sum", "round"):
            return self._call(self._eat())
        if token is None:
            raise ExprError("missing a value")
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            self._eat()
            return float(token)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            self._eat()
            if token not in self.env:
                raise ExprError(f"unknown name {token}")
            return float(self.env[token])
        raise ExprError(f"unexpected '{token}'")

    def _call(self, name: str) -> float:
        self._eat("(")
        args = [self._expr()]
        while self._peek() == ",":
            self._eat(",")
            args.append(self._expr())
        self._eat(")")
        if name == "sum":
            return float(sum(args))
        if len(args) == 1:
            return float(round(args[0]))
        if len(args) == 2:
            return float(round(args[0], int(args[1])))
        raise ExprError("round takes one or two arguments")


def _connect(db=None):
    config.ensure_dirs()
    con = sqlite3.connect(db or config.DB_PATH)
    con.execute(SCHEMA)
    return _Closing(con)


class _Closing:
    def __init__(self, con):
        self.con = con

    def __enter__(self):
        return self.con

    def __exit__(self, *exc):
        self.con.commit()
        self.con.close()


def _row(raw) -> dict:
    keys = ("id", "target_kind", "target_id", "action", "payload", "reason", "author", "created_at")
    item = dict(zip(keys, raw))
    item["payload"] = json.loads(item["payload"])
    return item
