# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A terminal tool that answers plain-English questions about a furniture inventory by
translating them into read-only SQL via an LLM, validating and executing that SQL
against SQLite, and composing a natural-language answer. See `docs/plan.md` for the
original build spec (fixed technical decisions, exact prompt text, and acceptance
criteria) — treat it as the source of truth if behavior here seems to deviate from it.

## Commands

Package management is via `uv` (not pip/venv directly).

```bash
uv sync                          # install/sync dependencies
uv add <package>                 # add a new dependency (never hand-edit uv.lock)
uv run python db/seed.py         # (re)create db/furniture.db with mock data
uv run python chat.py            # start the terminal chat REPL
uv run python tests/test_sql_guard.py   # run the safety/unit tests (plain script, no pytest runner)
```

There is no build step or linter configured. `.env` must contain `OPENROUTER_API_KEY`
(copy from `.env.example`); `chat.py` exits non-zero immediately if it's missing.

Manual/acceptance test scenarios (breakdown queries, clarify round-trips, safety
checks) are enumerated in `tests/test_manual.md` — run them by hand against the live
REPL when changing prompt or graph-routing behavior.

## Architecture

Each user turn runs through a LangGraph `StateGraph` (`pipeline/graph.py`) with four
nodes defined in `pipeline/nodes.py`:

1. **generate_sql** — LLM call using `SQL_GENERATION_PROMPT` (`pipeline/prompts.py`).
   Returns raw JSON: either `{"action": "query", "sql": ...}` or
   `{"action": "clarify", "question": ...}`. Defaults to a GROUP BY breakdown for
   broad category questions rather than asking unnecessary clarifying questions.
2. **validate_sql** — `pipeline/sql_guard.py`, pure `sqlglot`-based validation, no LLM.
   Enforces: single statement, SELECT-only, known tables/columns only (via the
   `ALLOWED` dict, alias-aware), no denylisted functions. Returns `(is_valid, reason)`;
   `reason` is fed back into the next `generate_sql` retry.
3. **execute_query** — `pipeline/db.py`, runs the validated SQL against a SQLite
   connection opened `mode=ro` (`file:...?mode=ro`, `uri=True`) — a second,
   independent safety layer beneath the validator. Results are capped at 500 rows.
4. **compose_answer** — a *separate* LLM call using `ANSWER_COMPOSITION_PROMPT`. It
   receives only `{question, rows}` as JSON — never SQL-generation ability — so
   malicious content in a data field cannot trigger further query execution.

Routing (`MAX_ATTEMPTS = 2`, defined in `pipeline/nodes.py`):
`generate_sql` → clarify → END, or → `validate_sql` → (valid → `execute_query`,
invalid + attempts left → back to `generate_sql`, invalid + attempts exhausted →
`compose_answer` with a graceful fallback) → `execute_query` → (ok → `compose_answer`,
db error + attempts left → back to `generate_sql`). See the Mermaid diagram in
`README.md` for the visual version — keep both in sync when routing changes.

`pipeline/llm.py` wraps the OpenRouter-backed OpenAI client
(model `nvidia/nemotron-3-ultra-550b-a55b:free`, `base_url` pointed at
`https://openrouter.ai/api/v1`). `chat.py` maintains the `conversation` list across
REPL turns so clarify round-trips retain context, and prints the generated SQL dimmed
via `rich` for debugging — never surfaces raw SQL as part of the answer shown to the
user.

## Guardrails specific to this project

- Never weaken the two-layer safety model: the `sqlglot` validator in `sql_guard.py`
  and the read-only SQLite connection in `db.py` are both required independently —
  don't remove or bypass either even if the other seems sufficient.
- Keep `SQL_GENERATION_PROMPT` and `ANSWER_COMPOSITION_PROMPT` separate; never give the
  answer-composition call the ability to emit or execute SQL.
- Terminal-only interface. Do not introduce a web framework, TUI library, ORM, Docker,
  or JS frontend — `docs/plan.md` explicitly rules these out.
- When adding new tables/columns, update the `ALLOWED` dict in `pipeline/sql_guard.py`
  and `db/schema.sql` together, or the validator will reject otherwise-legitimate SQL.
