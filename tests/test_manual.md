# Manual Acceptance Tests

Run `uv run python db/seed.py` then `uv run python chat.py` and try each scenario.

## 1. Breakdown default
> how many tables do we have?

Expect: answer states 30 total with 12 coffee / 5 round / 10 square / 3 standing table breakdown. No clarifying question asked.

## 2. Direct count
> how many office chairs?

Expect: 25.

## 3. Total across everything
> how many pieces of furniture in total?

Expect: 242.

## 4. Clarify path
> tell me about the furniture

Expect: a clarifying question asking whether the user wants quantity, value, or location.

Follow up:
> the total value

Expect: a real answer using the prior turn as context when the LLM path is available.

## 5. Template path checks
These should answer without an LLM SQL-generation call:

- `how many tables do we have?`
- `how many pieces of furniture in total?`
- `where is our inventory?`
- `what categories do we carry?`

## 6. Safety: write attempt blocked (automated)
See `tests/test_sql_guard.py::test_delete_blocked`.

## 7. Safety: schema probe blocked (automated)
See `tests/test_sql_guard.py::test_schema_probe_blocked`.

## 8. Safety: statement chaining blocked (automated)
See `tests/test_sql_guard.py::test_statement_chaining_blocked`.

## 9. Read-only connection (automated)
See `tests/test_sql_guard.py::test_readonly_connection_blocks_write`.

Run automated tests with:
```bash
uv run python tests/test_sql_guard.py
uv run python tests/test_pipeline_templates.py
```
