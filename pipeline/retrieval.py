import re

from pipeline.semantic_layer import BUSINESS_SYNONYMS, JOINS, TABLES, semantic_context_text


def normalize_question_text(question: str) -> str:
    text = question.strip().lower()
    text = re.sub(r"\s+", " ", text)
    for source, target in sorted(BUSINESS_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return text


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_context(question: str, catalog: str, samples: dict[str, list[str]]) -> str:
    q_tokens = _tokens(question)
    lines = [semantic_context_text(), "", "RELEVANT SCHEMA CONTEXT:"]

    for table in TABLES:
        table_terms = {table.name, *table.synonyms}
        column_matches = []
        for column in table.columns:
            terms = {column.name, *column.synonyms}
            if q_tokens & _tokens(" ".join(terms)) or q_tokens & _tokens(column.description):
                column_matches.append(column)

        if q_tokens & _tokens(" ".join(table_terms)) or column_matches:
            lines.append(f"- {table.name}: {table.description}")
            for column in column_matches or table.columns:
                lines.append(f"  - {column.name}: {column.description}")

    if "category" in q_tokens or any(value in question for value in samples.get("categories", [])):
        lines.append("")
        lines.append("KNOWN CATEGORIES:")
        lines.extend(f"- {value}" for value in samples.get("categories", []))

    if any(token in q_tokens for token in ("warehouse", "floor", "showroom", "location", "where")):
        lines.append("")
        lines.append("KNOWN LOCATIONS:")
        lines.extend(f"- {value}" for value in samples.get("locations", []))

    lines.append("")
    lines.append("CATALOG VALUES:")
    lines.append(catalog)
    lines.append("")
    lines.append("APPROVED JOIN PATHS:")
    for join in JOINS:
        lines.append(f"- {join['left']} = {join['right']}")
    return "\n".join(lines)
