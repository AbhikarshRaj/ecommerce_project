import csv
from collections import Counter

CSV_FILE = "marketlane_100_products.csv"

with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
    products = list(csv.DictReader(file))

print("=" * 60)
print("MARKETLANE PRODUCT CSV VALIDATION")
print("=" * 60)

# 1. Total products
print("\n1. Total products:", len(products))

# 2. Check duplicate product IDs
ids = [product["id"].strip() for product in products]
duplicates = [product_id for product_id, count in Counter(ids).items()
              if count > 1]

print("\n2. Duplicate IDs:", duplicates if duplicates else "None")

# 3. Check missing values
required_fields = [
    "id", "name", "category", "brand",
    "price_rupees", "colour", "stock"
]

missing = []

for row_number, product in enumerate(products, start=2):
    for field in required_fields:
        if not product.get(field, "").strip():
            missing.append(f"Row {row_number}: {field}")

print("\n3. Missing required values:")
print(missing if missing else "None")

# 4. Validate prices
invalid_prices = []

for product in products:
    try:
        if float(product["price_rupees"]) <= 0:
            invalid_prices.append(product["id"])
    except (ValueError, TypeError):
        invalid_prices.append(product["id"])

print("\n4. Invalid prices:",
      invalid_prices if invalid_prices else "None")

# 5. Validate stock
invalid_stock = []

for product in products:
    try:
        if int(product["stock"]) < 0:
            invalid_stock.append(product["id"])
    except (ValueError, TypeError):
        invalid_stock.append(product["id"])

print("\n5. Invalid stock:",
      invalid_stock if invalid_stock else "None")

# 6. Category distribution
print("\n6. Category distribution:")

for category, count in Counter(
    product["category"] for product in products
).items():
    print(f"{category}: {count}")

print("\n" + "=" * 60)
print("VALIDATION COMPLETED")
print("=" * 60)