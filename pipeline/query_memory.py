from difflib import SequenceMatcher

from pipeline.retrieval import normalize_question_text

SCHEMA_VERSION = "furniture-v1"
_MEMORY: list[dict] = []


def lookup(question: str) -> dict | None:
    normalized = normalize_question_text(question)
    best: tuple[float, dict] | None = None
    for entry in _MEMORY:
        if entry.get("schema_version") != SCHEMA_VERSION:
            continue
        score = SequenceMatcher(None, normalized, entry["question"]).ratio()
        if score >= 0.92 and (best is None or score > best[0]):
            best = (score, entry)
    return best[1] if best else None


def remember(question: str, sql: str, rows: list[dict], source: str, intent: dict | None = None) -> None:
    normalized = normalize_question_text(question)
    if any(entry["question"] == normalized and entry["sql"] == sql for entry in _MEMORY):
        return
    _MEMORY.append(
        {
            "question": normalized,
            "sql": sql,
            "result_shape": sorted(rows[0].keys()) if rows else [],
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "intent": intent or {},
        }
    )
