import os
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "furniture.db")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")

MAX_ROWS = 500
MAX_SQLITE_STEPS = 100_000


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql: str) -> list[dict]:
    conn = _connect()
    try:
        conn.set_progress_handler(lambda: 1, MAX_SQLITE_STEPS)
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
        return [dict(row) for row in rows]
    finally:
        conn.set_progress_handler(None, 0)
        conn.close()


def run_readonly(sql: str) -> list[dict]:
    return run_query(sql)


def explain(sql: str) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def introspect_schema() -> dict[str, list[str]]:
    conn = _connect()
    try:
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        schema = {}
        for table_row in table_rows:
            table = table_row["name"]
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
            schema[table] = [column["name"] for column in columns]
        return schema
    finally:
        conn.close()


def sample_values() -> dict[str, list[str]]:
    conn = _connect()
    try:
        categories = conn.execute(
            "SELECT name FROM furniture_category ORDER BY name"
        ).fetchall()
        subtypes = conn.execute(
            "SELECT subtype FROM furniture_item ORDER BY subtype"
        ).fetchall()
        locations = conn.execute(
            "SELECT DISTINCT location FROM furniture_item WHERE location IS NOT NULL ORDER BY location"
        ).fetchall()
        return {
            "categories": [row["name"] for row in categories],
            "subtypes": [row["subtype"] for row in subtypes],
            "locations": [row["location"] for row in locations],
        }
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
