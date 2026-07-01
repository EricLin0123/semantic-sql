import sqlglot
from sqlglot import exp

DENYLIST_FUNCTIONS = {
    "load_extension",
    "readfile",
    "writefile",
    "edit",
    "fts3_tokenizer",
}

ALLOWED = {
    "furniture_category": {"id", "name"},
    "furniture_item": {"id", "category_id", "subtype", "quantity", "location", "unit_price"},
}


def validate_sql(sql: str, allowed: dict[str, set[str]]) -> tuple[bool, str]:
    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        return False, f"failed to parse SQL: {e}"

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return False, "only a single SQL statement is allowed"

    stmt = statements[0]

    if not isinstance(stmt, exp.Select):
        return False, "only SELECT statements are allowed"

    alias_to_table = {}
    for table in stmt.find_all(exp.Table):
        table_name = table.name
        if table_name not in allowed:
            return False, f"table '{table_name}' is not allowed"
        alias = table.alias or table_name
        alias_to_table[alias] = table_name

    for column in stmt.find_all(exp.Column):
        col_name = column.name
        if col_name in ("*", ""):
            continue
        table_ref = column.table
        if table_ref:
            actual_table = alias_to_table.get(table_ref)
            if actual_table is None or col_name not in allowed[actual_table]:
                return False, f"column '{table_ref}.{col_name}' is not allowed"
        else:
            if not any(col_name in cols for cols in allowed.values()):
                return False, f"column '{col_name}' is not allowed"

    for func in stmt.find_all(exp.Anonymous):
        if func.name and func.name.lower() in DENYLIST_FUNCTIONS:
            return False, f"function '{func.name}' is not allowed"

    for func in stmt.find_all(exp.Func):
        name = func.sql_name().lower() if hasattr(func, "sql_name") else ""
        if name in DENYLIST_FUNCTIONS:
            return False, f"function '{name}' is not allowed"

    return True, ""
