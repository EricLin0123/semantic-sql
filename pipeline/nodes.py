import json
import re

from rich.console import Console

from pipeline.db import explain, get_category_catalog, run_readonly, sample_values
from pipeline.llm import chat
from pipeline.prompts import ANSWER_COMPOSITION_PROMPT, HISTORY_FALLBACK_PROMPT, sql_generation_prompt
from pipeline.query_memory import lookup, remember
from pipeline.retrieval import normalize_question_text, retrieve_context
from pipeline.sql_guard import ALLOWED, validate_sql
from pipeline.templates import classify_intent, find_catalog_match, sql_for_intent

MAX_ATTEMPTS = 2

_CATALOG = get_category_catalog()
_SAMPLES = sample_values()
_console = Console(stderr=True)


def _resolve_followup_question(question: str, conversation: list) -> str:
    normalized = normalize_question_text(question)
    if find_catalog_match(normalized, _SAMPLES["categories"], _SAMPLES["subtypes"]):
        return normalized
    if not re.search(r"\b(it|its|they|them|that|those|one)\b", normalized):
        return normalized

    for message in reversed(conversation):
        content = normalize_question_text(str(message.get("content", "")))
        match = find_catalog_match(content, _SAMPLES["categories"], _SAMPLES["subtypes"])
        if match:
            return f"{normalized} {match[1]}"
    return normalized


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


def _format_history_total_cost(quantity: int, unit_price: float) -> str:
    return f"The total cost is {quantity} * {_format_money(unit_price)} = {_format_money(quantity * unit_price)}."


def _answer_total_cost_from_history(question: str, conversation: list) -> str | None:
    normalized = normalize_question_text(question)
    if not re.search(r"\btotal\b", normalized) or not re.search(r"\b(cost|price|value|amount)\b", normalized):
        return None

    assistant_text = "\n".join(
        str(message.get("content", "")) for message in conversation[-8:] if message.get("role") == "assistant"
    )
    quantity_match = re.search(r"\b(?:you have|there are)\s+(\d+)\s+([a-z0-9 -]+?)(?:\.|$)", assistant_text, re.I)
    if not quantity_match:
        return None

    quantity = int(quantity_match.group(1))
    item = quantity_match.group(2).strip().rstrip("s")
    price_match = re.search(
        rf"\b(?:a|an|one)\s+{re.escape(item)}s?\s+costs\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)",
        assistant_text,
        re.I,
    )
    if not price_match:
        return None

    unit_price = float(price_match.group(1).replace(",", ""))
    return _format_history_total_cost(quantity, unit_price)


def _answer_from_history_or_none(state: dict) -> str | None:
    conversation = state.get("conversation") or []
    if not conversation:
        return None

    messages = list(conversation[-8:])
    messages.append({"role": "user", "content": state["question"]})
    try:
        raw = chat(HISTORY_FALLBACK_PROMPT, messages)
    except Exception as e:
        state["last_error"] = f"history fallback llm error: {e}"
    else:
        parsed = _parse_json_response(raw)
        if parsed is None:
            state["last_error"] = f"history fallback response was not valid JSON: {raw[:200]}"
        elif parsed.get("action") == "answer" and str(parsed.get("answer", "")).strip():
            return str(parsed["answer"]).strip()

    return _answer_total_cost_from_history(state["question"], conversation)


def normalize_question(state: dict) -> dict:
    state["normalized_question"] = _resolve_followup_question(state["question"], state.get("conversation", []))
    state.setdefault("trace", []).append({"node": "normalize_question"})
    return state


def classify_intent_node(state: dict) -> dict:
    memory_hit = lookup(state["normalized_question"])
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

    if intent.get("kind") == "fallback":
        fallback_answer = intent.get(
            "answer",
            "I can answer furniture inventory questions about quantity, price, value, category, and location.",
        )
        history_answer = _answer_from_history_or_none(state)
        state["answer"] = history_answer or fallback_answer
        state["sql"] = None
        state["sql_source"] = "history_fallback" if history_answer else "fallback"
        state.setdefault("trace", []).append(
            {"node": "generate_or_template_sql", "source": state.get("sql_source")}
        )
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

    try:
        raw = chat(sql_generation_prompt(state["context"]), messages)
    except Exception as e:
        state["answer"] = "I can answer furniture inventory questions about quantity, price, value, category, and location."
        state["last_error"] = f"llm error: {e}"
        state["failure_type"] = "llm_error"
        state["sql"] = None
        state["sql_source"] = "fallback"
        return state
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
    if template == "subtype_price":
        row = rows[0]
        return f"A {row.get('subtype')} costs {_format_money(row.get('unit_price'))}."
    if template == "category_price_breakdown":
        category = intent.get("category", "category")
        parts = ", ".join(f"{row['subtype']}: {_format_money(row.get('unit_price'))}" for row in rows)
        return f"Prices for {category} items are: {parts}."
    if template == "subtype_location":
        parts = ", ".join(f"{row['location']}: {row['quantity']}" for row in rows)
        return f"{rows[0].get('subtype')} is located at {parts}."
    if template == "category_location_breakdown":
        category = intent.get("category", "items")
        total = sum(row.get("quantity") or 0 for row in rows)
        parts = ", ".join(f"{row['location']}: {row['quantity']}" for row in rows)
        return f"You have {total} {category} items across locations: {parts}."
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
    try:
        answer = chat(ANSWER_COMPOSITION_PROMPT, [{"role": "user", "content": payload}])
    except Exception:
        answer = "I found matching inventory data, but could not format a detailed answer right now."
    state["answer"] = answer
    return state


compose_answer = format_answer


def record_trace(state: dict) -> dict:
    if state.get("sql") and state.get("rows") is not None and not state.get("last_error"):
        remember(
            state["normalized_question"],
            state["sql"],
            state["rows"],
            state.get("sql_source", "unknown"),
            state.get("intent"),
        )
    state.setdefault("trace", []).append({"node": "record_trace", "source": state.get("sql_source")})
    return state
