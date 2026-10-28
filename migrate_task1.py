"""Migration script for Task 1: Add is_active column to products table.

Preserves all existing records and defaults is_active to 1.
Backs up the database before making any changes.
"""
import datetime
import os
from pathlib import Path
import shutil
import sqlite3


def migrate_database(db_path=None):
    if db_path is None:
        base_dir = Path(__file__).resolve().parent
        db_path = base_dir / "instance" / "ecommerce.db"
    else:
        db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found at {db_path}. Nothing to migrate.")
        return False

    # 1. Create a timestamped backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.name}.bak_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"Backed up database to: {backup_path.name}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # 2. Check if is_active column already exists
        cursor = conn.execute("PRAGMA table_info(products)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "is_active" in columns:
            print("Column 'is_active' already exists in 'products' table. Migration already applied.")
            return True

        # 3. Apply schema migration preserving all existing rows
        with conn:
            conn.execute("ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))")
            conn.execute("CREATE INDEX IF NOT EXISTS products_active ON products(is_active)")
            # Trigger catalog cache invalidation revision bump
            conn.execute("UPDATE catalog_meta SET revision = revision + 1 WHERE id = 1")

        print("Successfully added 'is_active' column (DEFAULT 1) and 'products_active' index to products table.")
        print("Existing records preserved with is_active = 1.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
