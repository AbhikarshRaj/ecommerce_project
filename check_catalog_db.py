
import sqlite3

# Connect to your existing database
db = sqlite3.connect("instance/ecommerce.db")

print("\n========== MARKETLANE DATABASE CHECK ==========\n")

# 1. Total products
total = db.execute(
    "SELECT COUNT(*) FROM products"
).fetchone()[0]

print("TOTAL PRODUCTS:", total)

# 2. Categories
categories = db.execute(
    "SELECT name FROM categories ORDER BY name"
).fetchall()

print("\nCATEGORIES:")
for category in categories:
    print("-", category[0])

# 3. Total subcategories
subcategories = db.execute(
    "SELECT COUNT(*) FROM subcategories"
).fetchone()[0]

print("\nTOTAL SUBCATEGORIES:", subcategories)

# 4. Products with brand
brands = db.execute(
    """
    SELECT COUNT(*)
    FROM products
    WHERE brand IS NOT NULL AND TRIM(brand) != ''
    """
).fetchone()[0]

print("PRODUCTS WITH BRAND:", brands)

# 5. Products with colour
colours = db.execute(
    """
    SELECT COUNT(*)
    FROM products
    WHERE colour IS NOT NULL AND TRIM(colour) != ''
    """
).fetchone()[0]

print("PRODUCTS WITH COLOUR:", colours)

# 6. Wishlist table
wishlist = db.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'wishlist_items'
    """
).fetchone()

print("WISHLIST TABLE EXISTS:", wishlist is not None)

# 7. Product count category-wise
print("\nPRODUCTS CATEGORY-WISE:")

rows = db.execute(
    """
    SELECT c.name, COUNT(p.id)
    FROM categories c
    LEFT JOIN products p ON c.id = p.category_id
    GROUP BY c.id, c.name
    ORDER BY c.name
    """
).fetchall()

for name, count in rows:
    print(f"{name}: {count} products")

print("\n===============================================\n")

db.close()
