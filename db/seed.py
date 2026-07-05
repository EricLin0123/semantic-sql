import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "furniture.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

CATEGORIES = [
    "table",
    "chair",
    "couch",
    "desk",
    "bookshelf",
    "dresser",
    "bed frame",
    "nightstand",
    "cabinet",
]

ITEMS = [
    ("table", "square table", 10, "Warehouse A", 120.00),
    ("table", "round table", 5, "Warehouse A", 150.00),
    ("table", "standing table", 3, "Floor 2", 220.00),
    ("table", "coffee table", 12, "Warehouse B", 95.00),
    ("chair", "office chair", 25, "Floor 2", 85.00),
    ("chair", "dining chair", 15, "Warehouse B", 45.00),
    ("chair", "recliner", 6, "Showroom", 310.00),
    ("chair", "armchair", 20, "Warehouse A", 60.00),
    ("couch", "2-seat couch", 3, "Showroom", 640.00),
    ("couch", "3-seat couch", 2, "Showroom", 890.00),
    ("couch", "sectional couch", 4, "Warehouse B", 1200.00),
    ("desk", "standing desk", 8, "Floor 3", 410.00),
    ("desk", "corner desk", 4, "Floor 3", 300.00),
    ("desk", "writing desk", 9, "Warehouse A", 175.00),
    ("bookshelf", "5-shelf bookcase", 14, "Warehouse A", 130.00),
    ("bookshelf", "corner bookshelf", 6, "Floor 1", 160.00),
    ("bookshelf", "ladder shelf", 10, "Showroom", 95.00),
    ("dresser", "6-drawer dresser", 7, "Warehouse B", 340.00),
    ("dresser", "3-drawer dresser", 11, "Warehouse B", 210.00),
    ("bed frame", "queen bed frame", 5, "Floor 2", 450.00),
    ("bed frame", "king bed frame", 3, "Floor 2", 520.00),
    ("bed frame", "twin bed frame", 8, "Warehouse A", 260.00),
    ("nightstand", "single-drawer nightstand", 18, "Warehouse A", 65.00),
    ("nightstand", "2-drawer nightstand", 12, "Floor 1", 90.00),
    ("cabinet", "storage cabinet", 9, "Warehouse B", 220.00),
    ("cabinet", "filing cabinet", 13, "Floor 3", 150.00),
]


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    cur = conn.cursor()

    category_ids = {}
    for name in CATEGORIES:
        cur.execute("INSERT INTO furniture_category (name) VALUES (?)", (name,))
        category_ids[name] = cur.lastrowid

    for category, subtype, quantity, location, unit_price in ITEMS:
        cur.execute(
            "INSERT INTO furniture_item (category_id, subtype, quantity, location, unit_price) "
            "VALUES (?, ?, ?, ?, ?)",
            (category_ids[category], subtype, quantity, location, unit_price),
        )

    conn.commit()

    cat_count = cur.execute("SELECT COUNT(*) FROM furniture_category").fetchone()[0]
    item_count = cur.execute("SELECT COUNT(*) FROM furniture_item").fetchone()[0]
    conn.close()

    print(f"Seeded {DB_PATH}: {cat_count} categories, {item_count} items.")


if __name__ == "__main__":
    main()
