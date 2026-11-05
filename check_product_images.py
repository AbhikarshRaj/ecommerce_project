from run import app
from app.database import get_db
from pathlib import Path

with app.app_context():

    db = get_db()

    print("\n========== EXISTING PRODUCT IMAGES ==========\n")

    products = db.execute("""
        SELECT id, name, image_path
        FROM products
        ORDER BY name
    """).fetchall()

    for product in products:

        image_path = product["image_path"]

        if image_path:
            full_path = Path(app.static_folder) / image_path
            exists = full_path.exists()
        else:
            full_path = None
            exists = False

        print(f"Product: {product['name']}")
        print(f"Image path: {image_path}")
        print(f"Image exists: {exists}")

        if full_path:
            print(f"Full path: {full_path}")

        print("-" * 60)