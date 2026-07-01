import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.sql_guard import ALLOWED, validate_sql


def test_delete_blocked():
    is_valid, _ = validate_sql("DELETE FROM furniture_item", ALLOWED)
    assert is_valid is False


def test_schema_probe_blocked():
    is_valid, _ = validate_sql("SELECT * FROM sqlite_master", ALLOWED)
    assert is_valid is False


def test_statement_chaining_blocked():
    is_valid, _ = validate_sql("SELECT 1; DROP TABLE furniture_item", ALLOWED)
    assert is_valid is False


def test_valid_select_passes():
    is_valid, _ = validate_sql("SELECT subtype, SUM(quantity) FROM furniture_item GROUP BY subtype", ALLOWED)
    assert is_valid is True


def test_readonly_connection_blocks_write():
    from pipeline.db import _connect

    conn = _connect()
    try:
        raised = False
        try:
            conn.execute("INSERT INTO furniture_item (category_id, subtype, quantity) VALUES (1, 'x', 1)")
        except sqlite3.OperationalError:
            raised = True
        assert raised
    finally:
        conn.close()


if __name__ == "__main__":
    test_delete_blocked()
    test_schema_probe_blocked()
    test_statement_chaining_blocked()
    test_valid_select_passes()
    test_readonly_connection_blocks_write()
    print("All tests passed.")
