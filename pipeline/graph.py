from typing import TypedDict

from langgraph.graph import END, StateGraph

from pipeline.nodes import (
    MAX_ATTEMPTS,
    compose_answer,
    execute_query,
    generate_sql,
    validate_sql_node,
)


class State(TypedDict):
    question: str
    conversation: list
    sql: str | None
    last_error: str | None
    attempts: int
    rows: list | None
    answer: str | None
    clarify: str | None


def _route_after_generate(state: State) -> str:
    if state.get("clarify"):
        return "end"
    return "validate"


def _route_after_validate(state: State) -> str:
    if not state.get("last_error"):
        return "execute"
    if state.get("attempts", 0) < MAX_ATTEMPTS:
        return "generate"
    return "compose"


def _route_after_execute(state: State) -> str:
    if not state.get("last_error"):
        return "compose"
    if state.get("attempts", 0) < MAX_ATTEMPTS:
        return "generate"
    return "compose"


def build_graph():
    graph = StateGraph(State)

    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("execute_query", execute_query)
    graph.add_node("compose_answer", compose_answer)

    graph.set_entry_point("generate_sql")

    graph.add_conditional_edges(
        "generate_sql",
        _route_after_generate,
        {"end": END, "validate": "validate_sql"},
    )
    graph.add_conditional_edges(
        "validate_sql",
        _route_after_validate,
        {"execute": "execute_query", "generate": "generate_sql", "compose": "compose_answer"},
    )
    graph.add_conditional_edges(
        "execute_query",
        _route_after_execute,
        {"compose": "compose_answer", "generate": "generate_sql"},
    )
    graph.add_edge("compose_answer", END)

    return graph.compile()


_compiled_graph = None


def run_turn(question: str, conversation: list) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    initial_state: State = {
        "question": question,
        "conversation": conversation,
        "sql": None,
        "last_error": None,
        "attempts": 0,
        "rows": None,
        "answer": None,
        "clarify": None,
    }

    result = _compiled_graph.invoke(initial_state)

    if result.get("clarify"):
        return {"type": "clarify", "question": result["clarify"]}
    return {"type": "answer", "answer": result.get("answer", "")}
