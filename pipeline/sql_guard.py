import sqlglot
from sqlglot import exp

from pipeline.semantic_layer import APPROVED_FUNCTIONS, allowed_schema

DENYLIST_FUNCTIONS = {
    "load_extension",
    "readfile",
    "writefile",
    "edit",
    "fts3_tokenizer",
}

ALLOWED = allowed_schema()
DISALLOWED_EXPRESSION_NAMES = {
    "alter",
    "attach",
    "command",
    "create",
    "delete",
    "drop",
    "insert",
    "pragma",
    "truncate",
    "update",
}


def _function_name(func: exp.Expression) -> str:
    if isinstance(func, exp.Anonymous):
        return func.name.lower()
    name = func.sql_name() if hasattr(func, "sql_name") else ""
    return name.lower()


def _collect_ctes(stmt: exp.Expression) -> set[str]:
    with_expr = stmt.args.get("with_")
    if not with_expr:
        return set()
    if with_expr.args.get("recursive"):
        raise ValueError("recursive CTEs are not allowed")

    cte_names = set()
    for cte in with_expr.find_all(exp.CTE):
        if not isinstance(cte.this, exp.Select):
            raise ValueError("CTEs must contain SELECT statements only")
        alias = cte.alias
        if not alias:
            raise ValueError("CTEs must have an alias")
        cte_names.add(alias)
    return cte_names


def _projection_is_aggregate_or_literal(projection: exp.Expression) -> bool:
    expression = projection.this if isinstance(projection, exp.Alias) else projection
    if isinstance(expression, (exp.Literal, exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)):
        return True
    if isinstance(expression, exp.Round):
        return any(isinstance(child, (exp.Sum, exp.Avg, exp.Min, exp.Max, exp.Count)) for child in expression.walk())
    return any(isinstance(child, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)) for child in expression.walk())


def _returns_single_aggregate_row(stmt: exp.Select) -> bool:
    if stmt.args.get("group"):
        return False
    projections = stmt.expressions or []
    return bool(projections) and all(_projection_is_aggregate_or_literal(projection) for projection in projections)


def _has_limit(stmt: exp.Select) -> bool:
    return stmt.args.get("limit") is not None


def validate_sql(sql: str, allowed: dict[str, set[str]] | None = None) -> tuple[bool, str]:
    allowed = allowed or ALLOWED
    lowered = sql.lower()
    if "--" in sql or "/*" in sql or "*/" in sql:
        return False, "SQL comments are not allowed"
    if any(token in lowered for token in ("sqlite_master", "sqlite_schema", "pragma", "attach")):
        return False, "schema probing and attachment are not allowed"

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

    for expression in stmt.walk():
        name = expression.__class__.__name__.lower()
        if name in DISALLOWED_EXPRESSION_NAMES:
            return False, f"{name.upper()} is not allowed"

    try:
        cte_names = _collect_ctes(stmt)
    except ValueError as e:
        return False, str(e)

    if any(True for _ in stmt.find_all(exp.Star)):
        return False, "SELECT * is not allowed"

    alias_to_table = {}
    for table in stmt.find_all(exp.Table):
        table_name = table.name
        if table_name in cte_names:
            alias_to_table[table.alias or table_name] = table_name
            continue
        if table_name not in allowed:
            return False, f"table {table_name} is not allowed"
        alias_to_table[table.alias or table_name] = table_name

    base_table_present = any(table_name not in cte_names for table_name in alias_to_table.values())

    for column in stmt.find_all(exp.Column):
        col_name = column.name
        if col_name in ("*", ""):
            return False, "SELECT * is not allowed"
        table_ref = column.table
        if table_ref:
            actual_table = alias_to_table.get(table_ref)
            if actual_table in cte_names:
                continue
            if actual_table is None or col_name not in allowed[actual_table]:
                return False, f"column {table_ref}.{col_name} is not allowed"
        else:
            if not any(col_name in cols for cols in allowed.values()):
                if base_table_present:
                    return False, f"column {col_name} is not allowed"
                continue

    for func in stmt.find_all(exp.Anonymous):
        name = _function_name(func)
        if name in DENYLIST_FUNCTIONS or name not in APPROVED_FUNCTIONS:
            return False, f"function {name} is not allowed"

    for func in stmt.find_all(exp.Func):
        name = _function_name(func)
        if name and (name in DENYLIST_FUNCTIONS or name not in APPROVED_FUNCTIONS):
            return False, f"function {name} is not allowed"

    if not _returns_single_aggregate_row(stmt) and not _has_limit(stmt):
        return False, "row-returning SELECT statements must include LIMIT"

    return True, ""
