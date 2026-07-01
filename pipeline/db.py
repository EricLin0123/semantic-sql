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


def get_category_catalog() -> str:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT furniture_category.name AS category, furniture_item.subtype AS subtype "
            "FROM furniture_category "
            "JOIN furniture_item ON furniture_item.category_id = furniture_category.id "
            "ORDER BY furniture_category.name, furniture_item.subtype"
        ).fetchall()
    finally:
        conn.close()

    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(row["category"], []).append(row["subtype"])

    return "\n".join(
        f"- {category}: {', '.join(subtypes)}" for category, subtypes in by_category.items()
    )
