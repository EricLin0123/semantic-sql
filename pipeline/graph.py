from typing import TypedDict

from langgraph.graph import END, StateGraph

from pipeline.nodes import (
    MAX_ATTEMPTS,
    classify_intent_node,
    dry_run_explain,
    execute_query,
    format_answer,
    generate_or_template_sql,
    normalize_question,
    record_trace,
    retrieve_context_node,
    validate_sql_node,
)


class State(TypedDict):
    question: str
    normalized_question: str | None
    conversation: list
    intent: dict | None
    context: str | None
    sql: str | None
    sql_source: str | None
    last_error: str | None
    failure_type: str | None
    attempts: int
    rows: list | None
    answer: str | None
    clarify: str | None
    explain: list | None
    memory_hit: dict | None
    trace: list


def _route_after_generate(state: State) -> str:
    if state.get("clarify") or state.get("answer"):
        return "end"
    return "validate"


def _can_retry(state: State) -> bool:
    return state.get("sql_source") == "llm" and state.get("attempts", 0) < MAX_ATTEMPTS


def _route_after_validate(state: State) -> str:
    if not state.get("last_error"):
        return "explain"
    if _can_retry(state):
        return "generate"
    return "format"


def _route_after_explain(state: State) -> str:
    if not state.get("last_error"):
        return "execute"
    if _can_retry(state):
        return "generate"
    return "format"


def _route_after_execute(state: State) -> str:
    if not state.get("last_error") or state.get("failure_type") == "empty_result":
        return "format"
    if _can_retry(state):
        return "generate"
    return "format"


def build_graph():
    graph = StateGraph(State)

    graph.add_node("normalize_question", normalize_question)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_or_template_sql", generate_or_template_sql)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("dry_run_explain", dry_run_explain)
    graph.add_node("execute", execute_query)
    graph.add_node("format_answer", format_answer)
    graph.add_node("record_trace", record_trace)

    graph.set_entry_point("normalize_question")
    graph.add_edge("normalize_question", "classify_intent")
    graph.add_edge("classify_intent", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_or_template_sql")
    graph.add_conditional_edges(
        "generate_or_template_sql",
        _route_after_generate,
        {"end": END, "validate": "validate_sql"},
    )
    graph.add_conditional_edges(
        "validate_sql",
        _route_after_validate,
        {"explain": "dry_run_explain", "generate": "generate_or_template_sql", "format": "format_answer"},
    )
    graph.add_conditional_edges(
        "dry_run_explain",
        _route_after_explain,
        {"execute": "execute", "generate": "generate_or_template_sql", "format": "format_answer"},
    )
    graph.add_conditional_edges(
        "execute",
        _route_after_execute,
        {"format": "format_answer", "generate": "generate_or_template_sql"},
    )
    graph.add_edge("format_answer", "record_trace")
    graph.add_edge("record_trace", END)

    return graph.compile()


_compiled_graph = None


def run_turn(question: str, conversation: list) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    initial_state: State = {
        "question": question,
        "normalized_question": None,
        "conversation": conversation,
        "intent": None,
        "context": None,
        "sql": None,
        "sql_source": None,
        "last_error": None,
        "failure_type": None,
        "attempts": 0,
        "rows": None,
        "answer": None,
        "clarify": None,
        "explain": None,
        "memory_hit": None,
        "trace": [],
    }

    result = _compiled_graph.invoke(initial_state)

    if result.get("clarify"):
        return {"type": "clarify", "question": result["clarify"]}
    return {"type": "answer", "answer": result.get("answer", "")}
