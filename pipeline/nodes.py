import json

from rich.console import Console

from pipeline.db import get_category_catalog, get_schema_ddl, run_query
from pipeline.llm import chat
from pipeline.prompts import ANSWER_COMPOSITION_PROMPT, sql_generation_prompt
from pipeline.sql_guard import ALLOWED, validate_sql

MAX_ATTEMPTS = 2

_SCHEMA_DDL = get_schema_ddl()
_CATALOG = get_category_catalog()
_console = Console(stderr=True)


def _parse_json_response(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_sql(state: dict) -> dict:
    messages = list(state.get("conversation", []))
    question = state["question"]
    if state.get("last_error"):
        question = (
            f"{question}\n\n"
            f"Your previous SQL was rejected: {state['last_error']}. "
            f"Produce a corrected SELECT."
        )
    messages.append({"role": "user", "content": question})

    raw = chat(sql_generation_prompt(_SCHEMA_DDL, _CATALOG), messages)
    parsed = _parse_json_response(raw)

    state["attempts"] = state.get("attempts", 0) + 1

    if parsed is None:
        state["last_error"] = f"response was not valid JSON: {raw[:200]}"
        state["sql"] = None
        state["clarify"] = None
        return state

    action = parsed.get("action")
    if action == "clarify":
        state["clarify"] = parsed.get("question", "Could you clarify your question?")
        state["sql"] = None
    elif action == "query":
        state["sql"] = parsed.get("sql", "")
        state["clarify"] = None
        _console.print(f"[dim]\\[debug] generated SQL: {state['sql']}[/dim]")
    elif action == "not_found":
        state["clarify"] = None
        state["sql"] = None
        item = parsed.get("item", "that item")
        state["answer"] = (
            f"We don't carry \"{item}\" — our inventory only covers: "
            f"table, chair, couch, desk, bookshelf, dresser, bed frame, "
            f"nightstand, and cabinet."
        )
    else:
        state["last_error"] = f"unrecognized action: {action!r}"
        state["sql"] = None
        state["clarify"] = None

    return state


def validate_sql_node(state: dict) -> dict:
    sql = state.get("sql")
    if not sql:
        state["last_error"] = state.get("last_error") or "no SQL was produced"
        return state

    is_valid, reason = validate_sql(sql, ALLOWED)
    if is_valid:
        state["last_error"] = None
    else:
        state["last_error"] = reason
        state["sql"] = None
    return state


def execute_query(state: dict) -> dict:
    try:
        rows = run_query(state["sql"])
        state["rows"] = rows
        state["last_error"] = None
    except Exception as e:
        state["last_error"] = f"database error: {e}"
        state["rows"] = None
        state["sql"] = None
    return state


def compose_answer(state: dict) -> dict:
    question = state["question"]
    rows = state.get("rows")

    if rows is None and state.get("last_error"):
        state["answer"] = (
            "I couldn't build a valid query for that — could you rephrase?"
        )
        return state

    payload = json.dumps({"question": question, "rows": rows if rows is not None else []})
    answer = chat(ANSWER_COMPOSITION_PROMPT, [{"role": "user", "content": payload}])
    state["answer"] = answer
    return state
