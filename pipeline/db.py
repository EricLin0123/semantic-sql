import os
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "furniture.db")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")

MAX_ROWS = 500


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql: str) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_schema_ddl() -> str:
    with open(_SCHEMA_PATH) as f:
        return f.read()
