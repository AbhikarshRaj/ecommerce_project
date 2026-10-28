
"""SQLite persistence. Connections are scoped to a Flask request."""

import json
import sqlite3
import unicodedata
from pathlib import Path

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS subcategories (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    UNIQUE(category_id, normalized_name),
    UNIQUE(id, category_id)
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    subcategory_id INTEGER,
    price_paise INTEGER NOT NULL CHECK(price_paise >= 0),
    stock INTEGER NOT NULL CHECK(stock >= 0),
    image_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(subcategory_id, category_id)
        REFERENCES subcategories(id, category_id)
);

CREATE INDEX IF NOT EXISTS products_category
ON products(category_id);

CREATE INDEX IF NOT EXISTS products_subcategory
ON products(subcategory_id);

CREATE TABLE IF NOT EXISTS catalog_meta (
    id INTEGER PRIMARY KEY CHECK(id=1),
    revision INTEGER NOT NULL
);

INSERT OR IGNORE INTO catalog_meta VALUES (1, 0);

CREATE TRIGGER IF NOT EXISTS product_insert
AFTER INSERT ON products
BEGIN
    UPDATE catalog_meta SET revision=revision+1 WHERE id=1;
END;

CREATE TRIGGER IF NOT EXISTS product_update
AFTER UPDATE ON products
BEGIN
    UPDATE catalog_meta SET revision=revision+1 WHERE id=1;
END;

CREATE TRIGGER IF NOT EXISTS product_delete
AFTER DELETE ON products
BEGIN
    UPDATE catalog_meta SET revision=revision+1 WHERE id=1;
END;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    total_paise INTEGER NOT NULL CHECK(total_paise >= 0),
    payment_method TEXT NOT NULL DEFAULT 'COD'
        CHECK(payment_method = 'COD'),
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending', 'Processing', 'Shipped', 'Delivered')),
    cart_version INTEGER NOT NULL,
    submission_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    unit_price_paise INTEGER NOT NULL CHECK(unit_price_paise >= 0),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    line_total_paise INTEGER NOT NULL CHECK(line_total_paise >= 0)
);

CREATE INDEX IF NOT EXISTS orders_status_created
ON orders(status, created_at, id);

CREATE INDEX IF NOT EXISTS orders_customer
ON orders(customer_id, created_at);

CREATE INDEX IF NOT EXISTS order_items_order
ON order_items(order_id);

CREATE TABLE IF NOT EXISTS order_status_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL
        CHECK(new_status IN ('Pending', 'Processing', 'Shipped', 'Delivered')),
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT NOT NULL DEFAULT 'admin'
);

CREATE INDEX IF NOT EXISTS order_events_order
ON order_status_events(order_id, changed_at, id);
"""


def clean_name(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalized(value):
    return clean_name(value).casefold()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            timeout=10
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(_error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def category_id(db, name):
    name = clean_name(name)

    db.execute(
        "INSERT OR IGNORE INTO categories(name,normalized_name) VALUES (?,?)",
        (name, normalized(name))
    )

    return db.execute(
        "SELECT id FROM categories WHERE normalized_name=?",
        (normalized(name),)
    ).fetchone()["id"]


def subcategory_id(db, parent_id, name):
    name = clean_name(name)

    if not name:
        return None

    db.execute(
        """INSERT OR IGNORE INTO subcategories
        (category_id,name,normalized_name) VALUES (?,?,?)""",
        (parent_id, name, normalized(name))
    )

    return db.execute(
        """SELECT id FROM subcategories
        WHERE category_id=? AND normalized_name=?""",
        (parent_id, normalized(name))
    ).fetchone()["id"]


def initialize():
    db = get_db()

    # Create database tables and indexes.
    db.executescript(SCHEMA)

    # Add is_active column to existing products if it does not exist.
    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(products)")
    }

    if "is_active" not in columns:
        db.execute("""
            ALTER TABLE products
            ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
            CHECK(is_active IN (0, 1))
        """)
        db.commit()

    # Import original products only once.
    if not db.execute(
        "SELECT 1 FROM settings WHERE key='seed_imported'"
    ).fetchone():

        seed = Path(current_app.root_path) / "seed_products.json"

        products = (
            json.loads(seed.read_text(encoding="utf-8"))
            if seed.exists()
            else {}
        )

        with db:
            for pid, product in products.items():
                parent = category_id(db, product["category"])

                db.execute("""
                    INSERT OR IGNORE INTO products
                    (id, name, category_id, price_paise, stock, image_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    pid,
                    product["name"],
                    parent,
                    product["price_paise"],
                    product["stock"],
                    (
                        "uploads/products/f36de128e3794fad881b81f669ca8856.jpg"
                        if pid == "P101"
                        else f"images/products/{pid}.jpg"
                    )
                ))

            db.execute(
                "INSERT INTO settings VALUES ('seed_imported', 'yes')"
            )
