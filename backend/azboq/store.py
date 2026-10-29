"""Stage outputs in SQLite, keyed by stage name. Each row records the input hash it was built from."""
import json
import sqlite3
import time
from contextlib import contextmanager

from . import config
from .values import jsonable


@contextmanager
def connect():
    config.ensure_dirs()
    con = sqlite3.connect(config.DB_PATH)
    con.execute(
        "create table if not exists stage (name text primary key, input_hash text, built_at real, payload text)"
    )
    try:
        yield con
        con.commit()
    finally:
        con.close()


def put(name: str, payload, input_hash: str = ""):
    data = json.dumps(payload, ensure_ascii=False, default=jsonable, sort_keys=True)
    with connect() as con:
        con.execute(
            "insert or replace into stage (name, input_hash, built_at, payload) values (?, ?, ?, ?)",
            (name, input_hash, time.time(), data),
        )


def get(name: str):
    with connect() as con:
        row = con.execute("select payload from stage where name = ?", (name,)).fetchone()
    return json.loads(row[0]) if row else None


def input_hash(name: str) -> str | None:
    with connect() as con:
        row = con.execute("select input_hash from stage where name = ?", (name,)).fetchone()
    return row[0] if row else None


def names() -> list[str]:
    with connect() as con:
        return [r[0] for r in con.execute("select name from stage order by name")]
