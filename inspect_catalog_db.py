import sqlite3

DB_PATH = "instance/ecommerce.db"

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row

print("=" * 55)
print("MARKETLANE DATABASE INSPECTION")
print("=" * 55)

# Product table columns
print("\n1. PRODUCTS TABLE COLUMNS")

columns = connection.execute(
    "PRAGMA table_info(products)"
).fetchall()

for column in columns:
    print(f"{column['name']} ({column['type']})")

# Current product count
print("\n2. CURRENT PRODUCT COUNT")

count = connection.execute(
    "SELECT COUNT(*) FROM products"
).fetchone()[0]

print(count)

# Existing categories
print("\n3. EXISTING CATEGORIES")

categories = connection.execute(
    "SELECT id, name FROM categories ORDER BY name"
).fetchall()

for category in categories:
    print(f"{category['id']} - {category['name']}")

# Existing subcategories
print("\n4. EXISTING SUBCATEGORIES")

subcategories = connection.execute(
    "SELECT id, category_id, name FROM subcategories ORDER BY category_id, name"
).fetchall()

for subcategory in subcategories:
    print(
        f"{subcategory['id']} - "
        f"Category ID: {subcategory['category_id']} - "
        f"{subcategory['name']}"
    )

connection.close()

print("\nDATABASE INSPECTION COMPLETED")