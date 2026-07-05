from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    description: str
    synonyms: tuple[str, ...] = ()
    measure: bool = False


@dataclass(frozen=True)
class Table:
    name: str
    description: str
    columns: tuple[Column, ...]
    synonyms: tuple[str, ...] = ()


TABLES = (
    Table(
        name="furniture_category",
        description="One row per top-level furniture category the business carries.",
        synonyms=("category", "categories", "kind", "type"),
        columns=(
            Column("id", "Primary key for a category."),
            Column("name", "Category name such as table, chair, couch, or cabinet.", ("category", "kind", "type")),
        ),
    ),
    Table(
        name="furniture_item",
        description="Inventory rows for sellable furniture subtypes, quantities, locations, and unit prices.",
        synonyms=("inventory", "item", "items", "stock", "furniture"),
        columns=(
            Column("id", "Primary key for an inventory item."),
            Column("category_id", "Foreign key to furniture_category.id."),
            Column("subtype", "Specific product subtype, such as square table or office chair.", ("product", "style", "model")),
            Column("quantity", "Number of units currently in inventory.", ("count", "how many", "pieces", "stock"), True),
            Column("location", "Physical inventory location.", ("warehouse", "floor", "showroom", "where")),
            Column("unit_price", "Price for one unit of this subtype.", ("price", "cost"), True),
        ),
    ),
)

JOINS = (
    {
        "left": "furniture_item.category_id",
        "right": "furniture_category.id",
        "description": "Use this join when category names are needed with item inventory rows.",
    },
)

BUSINESS_SYNONYMS = {
    "sofa": "couch",
    "sofas": "couch",
    "loveseat": "couch",
    "bookcase": "bookshelf",
    "bookcases": "bookshelf",
    "shelf": "bookshelf",
    "shelves": "bookshelf",
    "bed": "bed frame",
    "beds": "bed frame",
    "bedframe": "bed frame",
    "bedframes": "bed frame",
    "night stand": "nightstand",
    "night stands": "nightstand",
    "stool": "chair",
    "stools": "chair",
}

APPROVED_FUNCTIONS = {
    "avg",
    "coalesce",
    "count",
    "max",
    "min",
    "round",
    "sum",
}

APPROVED_QUERY_TEMPLATES = (
    "total_quantity",
    "category_quantity_breakdown",
    "subtype_quantity",
    "location_breakdown",
    "total_inventory_value",
    "category_inventory_value",
    "category_list",
)


def allowed_schema() -> dict[str, set[str]]:
    return {table.name: {column.name for column in table.columns} for table in TABLES}


def semantic_context_text() -> str:
    lines = ["SEMANTIC LAYER:"]
    for table in TABLES:
        lines.append(f"- table {table.name}: {table.description}")
        if table.synonyms:
            lines.append(f"  synonyms: {', '.join(table.synonyms)}")
        for column in table.columns:
            measure = " measure" if column.measure else ""
            lines.append(f"  - {column.name}:{measure} {column.description}")
            if column.synonyms:
                lines.append(f"    synonyms: {', '.join(column.synonyms)}")
    lines.append("APPROVED JOINS:")
    for join in JOINS:
        lines.append(f"- {join['left']} = {join['right']}: {join['description']}")
    lines.append("APPROVED QUERY TEMPLATES:")
    for template in APPROVED_QUERY_TEMPLATES:
        lines.append(f"- {template}")
    return "\n".join(lines)
