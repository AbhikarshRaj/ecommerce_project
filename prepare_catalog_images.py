
import csv
import shutil
from pathlib import Path

# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

CSV_FILE = Path("marketlane_100_products.csv")

OUTPUT_FILE = Path("marketlane_100_products_prepared.csv")

IMAGE_DIR = Path("app/static/images/products")

PLACEHOLDER_PATH = "images/products/placeholder.png"


def main():

    print("=" * 60)
    print("MARKETLANE IMAGE PATH PREPARATION")
    print("=" * 60)

    # 1. Check input CSV
    if not CSV_FILE.exists():
        print("ERROR: Product CSV not found!")
        return

    # 2. Check placeholder image
    placeholder_file = IMAGE_DIR / "placeholder.png"

    if not placeholder_file.exists():
        print(f"ERROR: Placeholder not found: {placeholder_file}")
        return

    # 3. Read CSV
    try:
        with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            products = list(reader)

    except PermissionError:
        print("ERROR: Cannot read the CSV. Close Excel or other programs using it.")
        return

    if not products:
        print("ERROR: CSV contains no products!")
        return

    required_columns = {"id", "image_path"}

    if not fieldnames or not required_columns.issubset(fieldnames):
        print("ERROR: CSV must contain id and image_path columns!")
        return

    # 4. Prepare image paths
    matched = []
    placeholders = []

    for product in products:

        product_id = product["id"].strip()

        possible_images = [
            IMAGE_DIR / f"{product_id}.png",
            IMAGE_DIR / f"{product_id}.jpg",
            IMAGE_DIR / f"{product_id}.jpeg"
        ]

        found_image = next(
            (image for image in possible_images if image.is_file()),
            None
        )

        if found_image:

            product["image_path"] = (
                f"images/products/{found_image.name}"
            )

            matched.append(product_id)

        else:

            product["image_path"] = PLACEHOLDER_PATH

            placeholders.append(product_id)

    # 5. Write to a NEW CSV (original remains untouched)
    try:
        with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:

            writer = csv.DictWriter(file, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(products)

    except PermissionError:
        print("ERROR: Close the prepared CSV if it is already open.")
        return

    # 6. Display report
    print("\nIMAGE PREPARATION SUMMARY")
    print("-" * 60)

    print(f"Total products: {len(products)}")
    print(f"Individual images: {len(matched)}")
    print(f"Placeholder images: {len(placeholders)}")

    print("\nProducts with individual images:")
    print(", ".join(matched))

    print("\nProducts using placeholder:")
    print(", ".join(placeholders))

    print("\nOUTPUT FILE:")
    print(OUTPUT_FILE.resolve())

    print("\nImage paths prepared successfully!")


if __name__ == "__main__":
    main()
