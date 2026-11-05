
"""
Import the prepared 100-product MarketLane catalog into SQLite.

Run from the ecommerce_project root:
    python import_marketlane_catalog.py

Safety:
- Creates a timestamped SQLite backup before changing anything.
- Uses a single database transaction; errors roll back the catalog changes.
- Keeps shopping_carts and unrelated tables untouched.
- Replaces products and taxonomy with the five categories in the prepared CSV.
- Adds the material column if it is not already present.
- Supplies normalized_name for categories and subcategories.
"""

import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------

DB_FILE = Path("instance/ecommerce.db")
CSV_FILE = Path("marketlane_100_products_prepared.csv")
IMAGE_ROOT = Path("app/static")

EXPECTED_CATEGORIES = {
    "Electronics",
    "Clothing",
    "Footwear",
    "Home and Kitchen",
    "Books and Stationery",
}


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def normalize_name(name):
    """
    Generate a normalized name for database storage.

    Example:
        'Home and Kitchen' -> 'home and kitchen'
        '  Wireless Mouse  ' -> 'wireless mouse'
    """
    return " ".join(name.strip().lower().split())


def read_products():
    """
    Read and validate all 100 products from the prepared CSV.
    """

    if not CSV_FILE.is_file():
        raise FileNotFoundError(
            f"Prepared CSV not found: {CSV_FILE}"
        )

    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as file:

        reader = csv.DictReader(file)

        required_columns = {
            "id",
            "name",
            "category",
            "subcategory",
            "brand",
            "price_rupees",
            "price_paise",
            "colour",
            "gender",
            "size",
            "material",
            "stock",
            "is_active",
            "image_path",
        }

        if not reader.fieldnames or not required_columns.issubset(
            reader.fieldnames
        ):
            missing = required_columns - set(reader.fieldnames or [])

            raise ValueError(
                f"CSV is missing columns: {', '.join(sorted(missing))}"
            )

        products = list(reader)

    # Check total product count.
    if len(products) != 100:
        raise ValueError(
            f"Expected exactly 100 products, found {len(products)}."
        )

    # Check duplicate product IDs.
    product_ids = [
        row["id"].strip()
        for row in products
    ]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError("Duplicate product IDs found in CSV.")

    # Check category names.
    found_categories = {
        row["category"].strip()
        for row in products
    }

    if found_categories != EXPECTED_CATEGORIES:
        raise ValueError(
            "Unexpected category set.\n"
            f"Expected: {sorted(EXPECTED_CATEGORIES)}\n"
            f"Found: {sorted(found_categories)}"
        )

    # Validate every product.
    for row in products:

        product_id = row["id"].strip()
        image_path = row["image_path"].strip()

        if not product_id or not row["name"].strip():
            raise ValueError(
                "A product has a blank ID or name."
            )

        if not row["category"].strip():
            raise ValueError(
                f"Category is missing for {product_id}."
            )

        if not row["subcategory"].strip():
            raise ValueError(
                f"Subcategory is missing for {product_id}."
            )

        if int(row["price_paise"]) < 0 or int(row["stock"]) < 0:
            raise ValueError(
                f"Invalid price or stock for {product_id}."
            )

        if image_path.startswith("/") or ".." in Path(image_path).parts:
            raise ValueError(
                f"Unsafe image path for {product_id}: {image_path}"
            )

        full_image_path = IMAGE_ROOT / image_path

        if not full_image_path.is_file():
            raise FileNotFoundError(
                f"Image file for {product_id} does not exist: "
                f"{full_image_path}"
            )

    return products


def table_columns(connection, table_name):
    """
    Return all column names of a database table.
    """

    return {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        )
    }


# ------------------------------------------------------------
# 3. MAIN IMPORT FUNCTION
# ------------------------------------------------------------

def main():

    print("=" * 60)
    print("MARKETLANE 100-PRODUCT CATALOG IMPORT")
    print("=" * 60)

    # Check whether the database exists.
    if not DB_FILE.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_FILE}"
        )

    # Read and validate the CSV before touching the database.
    print("\nStep 1: Reading and validating CSV...")

    products = read_products()

    print(f"CSV validation successful: {len(products)} products.")

    # --------------------------------------------------------
    # STEP 2: CREATE DATABASE BACKUP
    # --------------------------------------------------------

    print("\nStep 2: Creating database backup...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_file = DB_FILE.with_name(
        f"ecommerce_before_import_{timestamp}.db"
    )

    shutil.copy2(DB_FILE, backup_file)

    print(f"Backup created: {backup_file}")

    # --------------------------------------------------------
    # STEP 3: CONNECT TO DATABASE
    # --------------------------------------------------------

    connection = sqlite3.connect(DB_FILE)

    connection.row_factory = sqlite3.Row

    try:

        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute("BEGIN IMMEDIATE")

        print("\nStep 3: Checking database structure...")

        product_columns = table_columns(
            connection,
            "products"
        )

        category_columns = table_columns(
            connection,
            "categories"
        )

        subcategory_columns = table_columns(
            connection,
            "subcategories"
        )

        # Ensure required normalized_name columns exist.
        if "normalized_name" not in category_columns:
            raise RuntimeError(
                "categories table is missing normalized_name."
            )

        if "normalized_name" not in subcategory_columns:
            raise RuntimeError(
                "subcategories table is missing normalized_name."
            )

        # Add material column if it does not exist.
        if "material" not in product_columns:

            connection.execute(
                "ALTER TABLE products ADD COLUMN material TEXT"
            )

            print("Added material column to products table.")

        else:
            print("Material column already exists.")

        # ----------------------------------------------------
        # STEP 4: CREATE OR RETRIEVE CATEGORIES
        # ----------------------------------------------------

        print("\nStep 4: Creating or retrieving categories...")

        category_ids = {}

        for category_name in sorted(EXPECTED_CATEGORIES):

            normalized_category = normalize_name(
                category_name
            )

            existing = connection.execute(
                """
                SELECT id
                FROM categories
                WHERE name = ?
                """,
                (category_name,)
            ).fetchone()

            if existing:

                category_ids[category_name] = existing["id"]

                print(
                    f"Existing category: {category_name}"
                )

            else:

                cursor = connection.execute(
                    """
                    INSERT INTO categories (
                        name,
                        normalized_name
                    )
                    VALUES (?, ?)
                    """,
                    (
                        category_name,
                        normalized_category
                    )
                )

                category_ids[category_name] = cursor.lastrowid

                print(
                    f"Created category: {category_name}"
                )

        # ----------------------------------------------------
        # STEP 5: DELETE OLD PRODUCTS
        # ----------------------------------------------------

        print("\nStep 5: Removing existing products...")

        connection.execute(
            "DELETE FROM products"
        )

        print("Existing products removed.")

        # ----------------------------------------------------
        # STEP 6: REMOVE OBSOLETE CATEGORIES
        # ----------------------------------------------------

        print("\nStep 6: Removing obsolete categories...")

        placeholders = ",".join(
            "?" for _ in EXPECTED_CATEGORIES
        )

        connection.execute(
            f"""
            DELETE FROM subcategories
            WHERE category_id IN (
                SELECT id
                FROM categories
                WHERE name NOT IN ({placeholders})
            )
            """,
            tuple(sorted(EXPECTED_CATEGORIES))
        )

        connection.execute(
            f"""
            DELETE FROM categories
            WHERE name NOT IN ({placeholders})
            """,
            tuple(sorted(EXPECTED_CATEGORIES))
        )

        print("Obsolete categories removed.")

        # ----------------------------------------------------
        # STEP 7: REBUILD SUBCATEGORIES
        # ----------------------------------------------------

        print("\nStep 7: Creating subcategories...")

        category_id_values = tuple(category_ids.values())

        category_placeholders = ",".join(
            "?" for _ in category_id_values
        )

        connection.execute(
            f"""
            DELETE FROM subcategories
            WHERE category_id IN ({category_placeholders})
            """,
            category_id_values
        )

        subcategory_ids = {}

        for row in products:

            category_name = row["category"].strip()

            subcategory_name = row["subcategory"].strip()

            key = (
                category_name,
                subcategory_name
            )

            # Create each category-subcategory combination once.
            if key not in subcategory_ids:

                normalized_subcategory = normalize_name(
                    subcategory_name
                )

                cursor = connection.execute(
                    """
                    INSERT INTO subcategories (
                        category_id,
                        name,
                        normalized_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        category_ids[category_name],
                        subcategory_name,
                        normalized_subcategory
                    )
                )

                subcategory_ids[key] = cursor.lastrowid

        print(
            f"Subcategories created: {len(subcategory_ids)}"
        )

        # ----------------------------------------------------
        # STEP 8: INSERT 100 PRODUCTS
        # ----------------------------------------------------

        print("\nStep 8: Importing products...")

        for index, row in enumerate(products, start=1):

            category_name = row["category"].strip()

            subcategory_name = row["subcategory"].strip()

            connection.execute(
                """
                INSERT INTO products (
                    id,
                    name,
                    category_id,
                    subcategory_id,
                    price_paise,
                    stock,
                    image_path,
                    created_at,
                    brand,
                    colour,
                    gender,
                    size,
                    is_active,
                    material
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    row["id"].strip(),
                    row["name"].strip(),
                    category_ids[category_name],
                    subcategory_ids[
                        (category_name, subcategory_name)
                    ],
                    int(row["price_paise"]),
                    int(row["stock"]),
                    row["image_path"].strip(),
                    row["brand"].strip(),
                    row["colour"].strip(),
                    row["gender"].strip(),
                    row["size"].strip(),
                    int(row["is_active"]),
                    row["material"].strip()
                )
            )

            print(
                f"{index:03d}/100 | "
                f"{row['id']} | "
                f"{row['name']}"
            )

        # ----------------------------------------------------
        # STEP 9: VERIFY IMPORT
        # ----------------------------------------------------

        print("\nStep 9: Verifying imported data...")

        imported_count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        category_count = connection.execute(
            "SELECT COUNT(*) FROM categories"
        ).fetchone()[0]

        subcategory_count = connection.execute(
            "SELECT COUNT(*) FROM subcategories"
        ).fetchone()[0]

        if imported_count != 100:
            raise RuntimeError(
                f"Expected 100 products, found {imported_count}."
            )

        if category_count != 5:
            raise RuntimeError(
                f"Expected 5 categories, found {category_count}."
            )

        # Check that every product has a valid category and subcategory.
        invalid_products = connection.execute(
            """
            SELECT COUNT(*)
            FROM products p
            LEFT JOIN categories c
                ON p.category_id = c.id
            LEFT JOIN subcategories s
                ON p.subcategory_id = s.id
                AND p.category_id = s.category_id
            WHERE c.id IS NULL OR s.id IS NULL
            """
        ).fetchone()[0]

        if invalid_products != 0:
            raise RuntimeError(
                f"{invalid_products} products have invalid category mappings."
            )

        # ----------------------------------------------------
        # STEP 10: COMMIT TRANSACTION
        # ----------------------------------------------------

        connection.commit()

        print("\n" + "=" * 60)
        print("MARKETLANE CATALOG IMPORT SUCCESSFUL")
        print("=" * 60)

        print(f"Products imported: {imported_count}")
        print(f"Categories: {category_count}")
        print(f"Subcategories: {subcategory_count}")

        print("Individual product images: 15")
        print("Placeholder images: 85")

        print("Material column: available")

        print(
            "Shopping carts and unrelated tables: left untouched"
        )

        print(f"Database backup: {backup_file}")

        # ----------------------------------------------------
        # STEP 11: DISPLAY PRODUCTS PER CATEGORY
        # ----------------------------------------------------

        print("\nProducts per category:")

        category_summary = connection.execute(
            """
            SELECT
                c.name,
                COUNT(p.id) AS product_count
            FROM categories c
            LEFT JOIN products p
                ON p.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name
            """
        ).fetchall()

        for row in category_summary:

            print(
                f"{row['name']}: "
                f"{row['product_count']} products"
            )

        print("\nImport completed and database changes committed.")

    except Exception:

        connection.rollback()

        print("\nIMPORT FAILED. Database changes were rolled back.")

        print(f"Backup is available at: {backup_file}")

        raise

    finally:

        connection.close()


# ------------------------------------------------------------
# 4. PROGRAM ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
