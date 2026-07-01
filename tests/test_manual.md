# Manual Acceptance Tests

Run `python db/seed.py` then `python chat.py` and try each scenario.

## 1. Breakdown default
> how many tables do we have?

Expect: answer states 18 total with 10 square / 5 round / 3 standing breakdown.
No clarifying question asked.

## 2. Direct count
> how many office chairs?

Expect: 25.

## 3. Total across everything
> how many pieces of furniture in total?

Expect: sum of all quantities (10+5+3+25+15+3+2+8+4 = 75).

## 4. Clarify path
> tell me about the furniture

Expect: a clarifying question (count, value, or location?).

Follow up:
> the total value

Expect: a real answer using the prior turn as context (no re-asking).

## 5. Safety: write attempt blocked (automated)
See `tests/test_sql_guard.py::test_delete_blocked` —
`validate_sql("DELETE FROM furniture_item", ALLOWED)` returns `is_valid is False`.

## 6. Safety: schema probe blocked (automated)
See `tests/test_sql_guard.py::test_schema_probe_blocked` —
`validate_sql("SELECT * FROM sqlite_master", ALLOWED)` returns `False`.

## 7. Safety: statement chaining blocked (automated)
See `tests/test_sql_guard.py::test_statement_chaining_blocked` —
`validate_sql("SELECT 1; DROP TABLE furniture_item", ALLOWED)` returns `False`.

## 8. Read-only connection (automated)
See `tests/test_sql_guard.py::test_readonly_connection_blocks_write` —
an INSERT through the read-only connection in `pipeline/db.py` raises
`sqlite3.OperationalError`.

Run automated tests with:
```bash
python tests/test_sql_guard.py
```
