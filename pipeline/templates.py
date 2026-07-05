import re

from pipeline.retrieval import normalize_question_text


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def _quote(value: str) -> str:
    return value.replace("'", "''")


def _find_catalog_match(question: str, categories: list[str], subtypes: list[str]) -> tuple[str, str] | None:
    for subtype in sorted(subtypes, key=len, reverse=True):
        if re.search(rf"\b{re.escape(subtype)}s?\b", question):
            return "subtype", subtype
    for category in sorted(categories, key=len, reverse=True):
        if re.search(rf"\b{re.escape(category)}s?\b", question):
            return "category", category
    return None


def classify_intent(question: str, categories: list[str], subtypes: list[str]) -> dict:
    normalized = normalize_question_text(question)

    if _contains_any(normalized, ("tell me", "about furniture", "about the furniture", "overview")) and not _contains_any(
        normalized, ("count", "many", "total", "value", "worth", "location", "where", "list")
    ):
        return {"kind": "ambiguous", "reason": "missing requested metric"}

    match = _find_catalog_match(normalized, categories, subtypes)

    if _contains_any(normalized, ("value", "worth", "valuation")):
        if match and match[0] == "category":
            return {"kind": "template", "template": "category_inventory_value", "category": match[1]}
        return {"kind": "template", "template": "total_inventory_value"}

    if _contains_any(normalized, ("where", "location", "locations", "warehouse", "floor", "showroom")):
        return {"kind": "template", "template": "location_breakdown"}

    if _contains_any(normalized, ("categories", "kinds", "types carried", "what do we carry", "list")):
        return {"kind": "template", "template": "category_list"}

    if _contains_any(normalized, ("how many", "count", "quantity", "stock", "pieces")) or match:
        if match and match[0] == "subtype":
            return {"kind": "template", "template": "subtype_quantity", "subtype": match[1]}
        if match and match[0] == "category":
            return {"kind": "template", "template": "category_quantity_breakdown", "category": match[1]}
        return {"kind": "template", "template": "total_quantity"}

    return {"kind": "llm"}


def sql_for_intent(intent: dict) -> str | None:
    template = intent.get("template")
    if template == "total_quantity":
        return "SELECT SUM(quantity) AS quantity FROM furniture_item"
    if template == "category_quantity_breakdown":
        category = _quote(intent["category"])
        return (
            "SELECT furniture_item.subtype, SUM(furniture_item.quantity) AS quantity "
            "FROM furniture_item "
            "JOIN furniture_category ON furniture_item.category_id = furniture_category.id "
            f"WHERE furniture_category.name = '{category}' "
            "GROUP BY furniture_item.subtype "
            "ORDER BY furniture_item.subtype "
            "LIMIT 100"
        )
    if template == "subtype_quantity":
        subtype = _quote(intent["subtype"])
        return (
            "SELECT furniture_item.subtype, SUM(furniture_item.quantity) AS quantity "
            "FROM furniture_item "
            f"WHERE furniture_item.subtype = '{subtype}' "
            "GROUP BY furniture_item.subtype "
            "LIMIT 100"
        )
    if template == "location_breakdown":
        return (
            "SELECT COALESCE(location, 'Unknown') AS location, SUM(quantity) AS quantity "
            "FROM furniture_item "
            "GROUP BY COALESCE(location, 'Unknown') "
            "ORDER BY quantity DESC "
            "LIMIT 100"
        )
    if template == "total_inventory_value":
        return "SELECT ROUND(SUM(quantity * unit_price), 2) AS inventory_value FROM furniture_item"
    if template == "category_inventory_value":
        category = _quote(intent["category"])
        return (
            "SELECT furniture_category.name AS category, "
            "ROUND(SUM(furniture_item.quantity * furniture_item.unit_price), 2) AS inventory_value "
            "FROM furniture_item "
            "JOIN furniture_category ON furniture_item.category_id = furniture_category.id "
            f"WHERE furniture_category.name = '{category}' "
            "GROUP BY furniture_category.name "
            "LIMIT 100"
        )
    if template == "category_list":
        return "SELECT name AS category FROM furniture_category ORDER BY name LIMIT 100"
    return None
