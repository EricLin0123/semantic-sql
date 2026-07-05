import json

from rich.console import Console

from pipeline.db import explain, get_category_catalog, run_readonly, sample_values
from pipeline.llm import chat
from pipeline.prompts import ANSWER_COMPOSITION_PROMPT, sql_generation_prompt
from pipeline.query_memory import lookup, remember
from pipeline.retrieval import normalize_question_text, retrieve_context
from pipeline.sql_guard import ALLOWED, validate_sql
from pipeline.templates import classify_intent, sql_for_intent

MAX_ATTEMPTS = 2

_CATALOG = get_category_catalog()
_SAMPLES = sample_values()
_console = Console(stderr=True)


def _parse_json_response(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _failure(state: dict, reason: str, failure_type: str) -> dict:
    state["last_error"] = reason
    state["failure_type"] = failure_type
    state["sql"] = None
    return state


def normalize_question(state: dict) -> dict:
    state["normalized_question"] = normalize_question_text(state["question"])
    state.setdefault("trace", []).append({"node": "normalize_question"})
    return state


def classify_intent_node(state: dict) -> dict:
    memory_hit = lookup(state["question"])
    if memory_hit:
        state["memory_hit"] = memory_hit
        state["intent"] = memory_hit.get("intent") or {"kind": "cache"}
    else:
        state["memory_hit"] = None
        state["intent"] = classify_intent(
            state["normalized_question"],
            _SAMPLES["categories"],
            _SAMPLES["subtypes"],
        )
    state.setdefault("trace", []).append({"node": "classify_intent", "intent": state["intent"]})
    return state


def retrieve_context_node(state: dict) -> dict:
    state["context"] = retrieve_context(state["normalized_question"], _CATALOG, _SAMPLES)
    state.setdefault("trace", []).append({"node": "retrieve_context"})
    return state


def generate_or_template_sql(state: dict) -> dict:
    intent = state.get("intent") or {"kind": "llm"}

    if intent.get("kind") == "ambiguous":
        state["clarify"] = "What would you like to know: quantity, inventory value, or location?"
        state["sql"] = None
        state["sql_source"] = "clarify"
        return state

    if state.get("memory_hit"):
        state["sql"] = state["memory_hit"]["sql"]
        state["sql_source"] = "cache"
        state["attempts"] = state.get("attempts", 0) + 1
        return state

    if intent.get("kind") == "template":
        state["sql"] = sql_for_intent(intent)
        state["sql_source"] = "template"
        state["attempts"] = state.get("attempts", 0) + 1
        return state

    messages = list(state.get("conversation", []))
    question = state["question"]
    if state.get("last_error"):
        question = (
            f"{question}\\n\\n"
            f"Your previous SQL failed with {state.get('failure_type', 'unknown_error')}: "
            f"{state['last_error']}. Produce a corrected SELECT only."
        )
    messages.append({"role": "user", "content": question})

    raw = chat(sql_generation_prompt(state["context"]), messages)
    parsed = _parse_json_response(raw)
    state["attempts"] = state.get("attempts", 0) + 1
    state["sql_source"] = "llm"

    if parsed is None:
        return _failure(state, f"response was not valid JSON: {raw[:200]}", "parse_failure")

    action = parsed.get("action")
    if action == "clarify":
        state["clarify"] = parsed.get("question", "Could you clarify your question?")
        state["sql"] = None
    elif action == "query":
        state["sql"] = parsed.get("sql", "")
        state["clarify"] = None
        _console.print(f"[dim]\\[debug] generated SQL: {state['sql']}[/dim]")
    elif action == "not_found":
        item = parsed.get("item", "that item")
        state["clarify"] = None
        state["sql"] = None
        state["answer"] = (
            f"We do not carry {item}. The current inventory categories are: "
            f"{', '.join(_SAMPLES['categories'])}."
        )
    else:
        return _failure(state, f"unrecognized action: {action!r}", "parse_failure")

    state.setdefault("trace", []).append({"node": "generate_or_template_sql", "source": state.get("sql_source")})
    return state


# Backward-compatible name for older imports/tests.
generate_sql = generate_or_template_sql


def validate_sql_node(state: dict) -> dict:
    sql = state.get("sql")
    if not sql:
        state["last_error"] = state.get("last_error") or "no SQL was produced"
        state["failure_type"] = state.get("failure_type") or "parse_failure"
        return state

    is_valid, reason = validate_sql(sql, ALLOWED)
    if is_valid:
        state["last_error"] = None
        state["failure_type"] = None
    else:
        state["last_error"] = reason
        state["failure_type"] = "policy_failure"
        state["sql"] = None
    state.setdefault("trace", []).append({"node": "validate_sql", "valid": is_valid})
    return state


def dry_run_explain(state: dict) -> dict:
    try:
        state["explain"] = explain(state["sql"])
        state["last_error"] = None
        state["failure_type"] = None
    except Exception as e:
        state["last_error"] = f"database explain error: {e}"
        state["failure_type"] = "execution_error"
        state["sql"] = None
    state.setdefault("trace", []).append({"node": "dry_run_explain"})
    return state


def execute_query(state: dict) -> dict:
    try:
        rows = run_readonly(state["sql"])
        state["rows"] = rows
        state["last_error"] = None
        state["failure_type"] = "empty_result" if rows == [] else None
    except Exception as e:
        state["last_error"] = f"database error: {e}"
        state["failure_type"] = "execution_error"
        state["rows"] = None
        state["sql"] = None
    state.setdefault("trace", []).append({"node": "execute", "rows": len(state.get("rows") or [])})
    return state


def _format_money(value: float | int | None) -> str:
    return f"${float(value or 0):,.2f}"


def _deterministic_answer(state: dict) -> str | None:
    if state.get("sql_source") not in {"template", "cache"}:
        return None
    rows = state.get("rows") or []
    intent = state.get("intent") or {}
    template = intent.get("template")

    if not rows:
        return "No matching items were found."

    if template == "total_quantity":
        return f"You have {rows[0].get('quantity') or 0} pieces of furniture in total."
    if template == "category_quantity_breakdown":
        total = sum(row.get("quantity") or 0 for row in rows)
        category = intent.get("category", "items")
        parts = ", ".join(f"{row['quantity']} {row['subtype']}" for row in rows)
        return f"You have {total} {category} items in total: {parts}."
    if template == "subtype_quantity":
        row = rows[0]
        return f"You have {row.get('quantity') or 0} {row.get('subtype', 'matching items')}."
    if template == "location_breakdown":
        total = sum(row.get("quantity") or 0 for row in rows)
        parts = ", ".join(f"{row['location']}: {row['quantity']}" for row in rows)
        return f"You have {total} pieces across locations: {parts}."
    if template == "total_inventory_value":
        return f"Total inventory value is {_format_money(rows[0].get('inventory_value'))}."
    if template == "category_inventory_value":
        row = rows[0]
        return f"The {row.get('category')} inventory is worth {_format_money(row.get('inventory_value'))}."
    if template == "category_list":
        return "Current inventory categories are: " + ", ".join(row["category"] for row in rows) + "."
    return None


def format_answer(state: dict) -> dict:
    question = state["question"]
    rows = state.get("rows")

    if rows is None and state.get("last_error"):
        state["answer"] = "I could not build a valid query for that. Could you rephrase?"
        return state

    deterministic = _deterministic_answer(state)
    if deterministic is not None:
        state["answer"] = deterministic
        return state

    payload = json.dumps({"question": question, "rows": rows if rows is not None else []})
    answer = chat(ANSWER_COMPOSITION_PROMPT, [{"role": "user", "content": payload}])
    state["answer"] = answer
    return state


compose_answer = format_answer


def record_trace(state: dict) -> dict:
    if state.get("sql") and state.get("rows") is not None and not state.get("last_error"):
        remember(state["question"], state["sql"], state["rows"], state.get("sql_source", "unknown"), state.get("intent"))
    state.setdefault("trace", []).append({"node": "record_trace", "source": state.get("sql_source")})
    return state
