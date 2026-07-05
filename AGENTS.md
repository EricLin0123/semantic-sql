# Repository Guidelines

## Project Structure & Module Organization

This repository is a terminal natural-language query tool for a furniture SQLite database. `chat.py` is the REPL entry point. Core application logic lives in `pipeline/`: `graph.py` wires the LangGraph flow, `nodes.py` implements each step, `prompts.py` contains LLM prompts, `sql_guard.py` validates generated SQL, `db.py` opens the database read-only, and `llm.py` configures the OpenRouter-backed client. Database schema and seed data are in `db/`; design notes and acceptance criteria are in `docs/`; automated and manual tests are in `tests/`.

## Build, Test, and Development Commands

Use `uv` for dependency management.

```bash
uv sync                         # install or sync dependencies
cp .env.example .env            # then set OPENROUTER_API_KEY
uv run python db/seed.py        # create or refresh db/furniture.db
uv run python chat.py           # start the terminal chat REPL
uv run python tests/test_sql_guard.py  # run automated safety tests
```

There is no build step, pytest runner, or configured linter.

## Coding Style & Naming Conventions

Target Python 3.11 or newer. Follow the existing simple module style: 4-space indentation, snake_case functions and variables, uppercase constants such as `MAX_ATTEMPTS` and `ALLOWED`, and type hints where they clarify public helper behavior. Keep prompt text centralized in `pipeline/prompts.py`. Do not hand-edit `uv.lock`; use `uv add <package>`.

## Testing Guidelines

Automated tests are plain Python functions in `tests/test_sql_guard.py`; name new tests `test_<behavior>()` and keep them executable by the existing script pattern. Run the seed command before tests that need `db/furniture.db`. For graph or prompt changes, also run the manual scenarios in `tests/test_manual.md` through `uv run python chat.py`.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries such as `use uv` and `Adjust strategy for Null`. Keep commit subjects concise and focused on one change. Pull requests should describe the user-visible behavior change, list commands or manual scenarios run, and call out any schema, prompt, or safety-validator changes.

## Agent-Specific Instructions

Preserve the two-layer SQL safety model: `pipeline/sql_guard.py` must reject unsafe SQL, and `pipeline/db.py` must keep SQLite opened in read-only mode. Keep SQL generation and answer composition as separate LLM calls. If adding tables or columns, update both `db/schema.sql` and `ALLOWED` together. Do not introduce a web UI, ORM, Docker setup, or JavaScript frontend unless explicitly requested.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
