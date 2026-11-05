import csv

with open("marketlane_100_products.csv", "r", encoding="utf-8-sig") as file:
    products = list(csv.DictReader(file))

for product in products:
    print(
        f"{product['id']} | "
        f"{product['name']} | "
        f"{product['brand']} | "
        f"{product['category']}"
    )