CREATE TABLE furniture_category (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE          -- e.g. 'table', 'chair', 'couch'
);

CREATE TABLE furniture_item (
    id          INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES furniture_category(id),
    subtype     TEXT NOT NULL,         -- e.g. 'square table', 'round table'
    quantity    INTEGER NOT NULL,
    location    TEXT,                  -- e.g. 'Warehouse A'
    unit_price  REAL
);
