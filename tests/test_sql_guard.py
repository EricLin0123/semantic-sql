import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.sql_guard import ALLOWED, validate_sql


def assert_blocked(sql: str):
    is_valid, _ = validate_sql(sql, ALLOWED)
    assert is_valid is False


def assert_allowed(sql: str):
    is_valid, reason = validate_sql(sql, ALLOWED)
    assert is_valid is True, reason


def test_delete_blocked():
    assert_blocked("DELETE FROM furniture_item")


def test_schema_probe_blocked():
    assert_blocked("SELECT name FROM sqlite_master LIMIT 1")


def test_statement_chaining_blocked():
    assert_blocked("SELECT SUM(quantity) FROM furniture_item; DROP TABLE furniture_item")


def test_select_star_blocked():
    assert_blocked("SELECT * FROM furniture_item LIMIT 10")


def test_comments_blocked():
    assert_blocked("SELECT subtype FROM furniture_item -- hidden\nLIMIT 10")


def test_missing_limit_on_row_query_blocked():
    assert_blocked("SELECT subtype FROM furniture_item")


def test_unknown_function_blocked():
    assert_blocked("SELECT random() AS value FROM furniture_item LIMIT 1")


def test_unknown_column_blocked():
    assert_blocked("SELECT secret_margin FROM furniture_item LIMIT 1")


def test_recursive_cte_blocked():
    assert_blocked(
        "WITH RECURSIVE q(x) AS ("
        "SELECT 1 UNION ALL SELECT x + 1 FROM q LIMIT 3"
        ") SELECT x FROM q LIMIT 10"
    )


def test_valid_aggregate_select_passes_without_limit():
    assert_allowed("SELECT subtype, SUM(quantity) AS quantity FROM furniture_item GROUP BY subtype LIMIT 100")
    assert_allowed("SELECT SUM(quantity) AS quantity FROM furniture_item")


def test_valid_alias_join_passes():
    assert_allowed(
        "SELECT fi.subtype, SUM(fi.quantity) AS quantity "
        "FROM furniture_item AS fi "
        "JOIN furniture_category AS fc ON fi.category_id = fc.id "
        "WHERE fc.name = 'table' "
        "GROUP BY fi.subtype LIMIT 100"
    )


def test_valid_subquery_passes():
    assert_allowed(
        "SELECT subtype FROM furniture_item "
        "WHERE category_id IN (SELECT id FROM furniture_category WHERE name = 'table') "
        "LIMIT 100"
    )


def test_valid_readonly_cte_passes():
    assert_allowed(
        "WITH q AS (SELECT subtype, quantity FROM furniture_item) "
        "SELECT subtype FROM q LIMIT 10"
    )


def test_allowed_functions_pass():
    assert_allowed("SELECT ROUND(SUM(quantity * unit_price), 2) AS inventory_value FROM furniture_item")


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
    test_select_star_blocked()
    test_comments_blocked()
    test_missing_limit_on_row_query_blocked()
    test_unknown_function_blocked()
    test_unknown_column_blocked()
    test_recursive_cte_blocked()
    test_valid_aggregate_select_passes_without_limit()
    test_valid_alias_join_passes()
    test_valid_subquery_passes()
    test_valid_readonly_cte_passes()
    test_allowed_functions_pass()
    test_readonly_connection_blocks_write()
    print("All tests passed.")
