"""Comprehensive automated test suite for Task 1: Catalog and inventory.

Covers:
- Step 1: Product form, database schema, and validation.
- Step 2: Edit action in admin.
- Step 3: Modifying name, category, subcategory, price, and stock.
- Step 4: Optional image replacement and retaining original image.
- Step 5: Migration and is_active field preservation.
- Step 6: Activate / Deactivate actions and exclusion from shopping results & cart rejection.
- Step 7: CatalogStore index consistency and revision updates via SQLite triggers.
- Step 8 & 9: 40-50 products across 5 required categories with stock levels & local images.
"""
import os
import sys
from io import BytesIO
from pathlib import Path
import sqlite3
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PIL import Image
from app import create_app
from app.database import get_db


class Task1CatalogInventoryTestCase(unittest.TestCase):
    test_db = Path(__file__).parent / "instance" / "ecommerce_test.db"

    @classmethod
    def setUpClass(cls):
        if cls.test_db.exists():
            try:
                cls.test_db.unlink()
            except Exception:
                pass
        cls.app = create_app({
            "TESTING": True,
            "DATABASE": str(cls.test_db),
            "SECRET_KEY": "test-secret-key-12345",
            "WTF_CSRF_ENABLED": False,
        })
        # Set up test database
        with cls.app.app_context():
            db = get_db()
            db.execute("INSERT OR REPLACE INTO settings VALUES ('admin_password', 'scrypt:test_hash')")
            db.execute("INSERT OR REPLACE INTO settings VALUES ('admin_revision', 'test_rev_123')")
            db.commit()

    @classmethod
    def tearDownClass(cls):
        if cls.test_db.exists():
            try:
                cls.test_db.unlink()
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["admin_revision"] = "test_rev_123"
            sess["csrf"] = "test-csrf-token"

    def create_dummy_image(self):
        img_io = BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_io, "JPEG")
        img_io.seek(0)
        return img_io

    # --- Test 1: Database Schema & Migration Preservation ---
    def test_01_schema_has_is_active(self):
        with self.app.app_context():
            db = get_db()
            cols = [row["name"] for row in db.execute("PRAGMA table_info(products)").fetchall()]
            self.assertIn("is_active", cols, "Column 'is_active' must exist in 'products' table.")

    # --- Test 2: Add Product with is_active default ---
    def test_02_add_product_and_initial_state(self):
        img_io = self.create_dummy_image()
        data = {
            "csrf_token": "test-csrf-token",
            "name": "Test Wireless Mouse",
            "category": "Electronics",
            "subcategory": "Computer Accessories",
            "price": "999.00",
            "stock": "25",
            "is_active": "1",
            "image": (img_io, "test_mouse.jpg")
        }
        res = self.client.post("/admin/products", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            products = store.select(active_only=False)
            created = next((p for p in products.values() if p["name"] == "Test Wireless Mouse"), None)
            self.assertIsNotNone(created)
            self.assertEqual(created["price_paise"], 99900)
            self.assertEqual(created["stock"], 25)
            self.assertEqual(created["is_active"], 1)

    # --- Test 3: Edit Product (Name, Category, Subcategory, Price, Stock) ---
    def test_03_edit_product_fields(self):
        # Retrieve test product
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Test Wireless Mouse'").fetchone()
            self.assertIsNotNone(row)
            pid = row["id"]

        # Edit fields without uploading a new image (retaining existing image)
        edit_data = {
            "csrf_token": "test-csrf-token",
            "name": "Updated Wireless Mouse Pro",
            "category": "Electronics",
            "subcategory": "Computer Accessories",
            "price": "1499.50",
            "stock": "40",
            "is_active": "1"
        }
        res = self.client.post(f"/admin/products/{pid}/edit", data=edit_data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            updated = store.get(pid)
            self.assertIsNotNone(updated)
            self.assertEqual(updated["name"], "Updated Wireless Mouse Pro")
            self.assertEqual(updated["price_paise"], 149950)
            self.assertEqual(updated["stock"], 40)
            self.assertTrue(updated["image_path"].endswith(".jpg"))

    # --- Test 4: Edit Product with Optional Replacement Image ---
    def test_04_edit_product_replacement_image(self):
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id, image_path FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]
            orig_img = row["image_path"]

        new_img_io = self.create_dummy_image()
        edit_data = {
            "csrf_token": "test-csrf-token",
            "name": "Updated Wireless Mouse Pro",
            "category": "Electronics",
            "subcategory": "Computer Accessories",
            "price": "1499.50",
            "stock": "35",
            "is_active": "1",
            "image": (new_img_io, "replacement.jpg")
        }
        res = self.client.post(f"/admin/products/{pid}/edit", data=edit_data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            updated = store.get(pid)
            self.assertNotEqual(updated["image_path"], orig_img, "Image path should update when replacement is supplied.")

    # --- Test 5: Deactivate Action & Storefront Exclusion ---
    def test_05_deactivate_product_excludes_from_shopping(self):
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]

        # Deactivate via POST
        res = self.client.post(f"/admin/products/{pid}/deactivate", data={"csrf_token": "test-csrf-token"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            # Active only (storefront view)
            active_catalog = store.select(active_only=True)
            self.assertNotIn(pid, active_catalog, "Deactivated product must be excluded from customer catalog.")

            # Admin view (include inactive)
            admin_catalog = store.select(active_only=False)
            self.assertIn(pid, admin_catalog, "Deactivated product must still be visible in admin catalog.")
            self.assertEqual(admin_catalog[pid]["is_active"], 0)

        # Check storefront API endpoint
        api_res = self.client.get("/api/catalog")
        self.assertEqual(api_res.status_code, 200)
        self.assertNotIn("Updated Wireless Mouse Pro", api_res.get_json()["html"])

    # --- Test 6: Activate Action & Storefront Inclusion ---
    def test_06_activate_product_restores_to_shopping(self):
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]

        # Activate via POST
        res = self.client.post(f"/admin/products/{pid}/activate", data={"csrf_token": "test-csrf-token"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            active_catalog = store.select(active_only=True)
            self.assertIn(pid, active_catalog, "Activated product must appear in active shopping catalog.")

    # --- Test 7: Cart Rejection for Inactive Products ---
    def test_07_cart_rejects_inactive_product(self):
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]

        # Deactivate again
        self.client.post(f"/admin/products/{pid}/deactivate", data={"csrf_token": "test-csrf-token"})

        # Try to add inactive product to cart
        cart_res = self.client.post("/api/cart/action", data={
            "csrf_token": "test-csrf-token",
            "version": "0",
            "action": "add",
            "product_id": pid
        })
        self.assertEqual(cart_res.status_code, 404, "Attempting to add an inactive product should return 404.")
        self.assertIn("no longer available", cart_res.get_json()["error"])

    # --- Test 8: Cart Snapshot Marks Inactive Items as Unavailable ---
    def test_08_cart_snapshot_marks_unavailable(self):
        with self.app.app_context():
            db = get_db()
            # Reactivate product temporarily
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]
            db.execute("UPDATE products SET is_active=1 WHERE id=?", (pid,))
            db.commit()

        # Add to cart while active
        add_res = self.client.post("/api/cart/action", data={
            "csrf_token": "test-csrf-token",
            "version": "0",
            "action": "add",
            "product_id": pid
        })
        self.assertEqual(add_res.status_code, 200)
        v = add_res.get_json()["version"]

        # Now admin deactivates product
        self.client.post(f"/admin/products/{pid}/deactivate", data={"csrf_token": "test-csrf-token"})

        # Query cart state
        state_res = self.client.get("/api/cart")
        self.assertEqual(state_res.status_code, 200)
        items = state_res.get_json()["items"]
        item = next((i for i in items if i["id"] == pid), None)
        self.assertIsNotNone(item)
        self.assertTrue(item["unavailable"], "Inactive item in existing cart must be marked unavailable=True.")

    # --- Test 9: Quick Restock Endpoint ---
    def test_09_quick_restock(self):
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]

        res = self.client.post(f"/admin/products/{pid}/restock", data={
            "csrf_token": "test-csrf-token",
            "stock": "99"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            store = self.app.extensions["catalog_store"]
            updated = store.get(pid)
            self.assertEqual(updated["stock"], 99)

    # --- Test 10: CatalogStore Index Consistency and Triggers ---
    def test_10_index_consistency_and_revision_bump(self):
        with self.app.app_context():
            db = get_db()
            store = self.app.extensions["catalog_store"]
            # Trigger initial fresh load
            store.select()
            rev_before = store.revision

            # Direct DB update triggers SQLite AFTER UPDATE trigger
            db.execute("UPDATE products SET stock=50 WHERE name='Updated Wireless Mouse Pro'")
            db.commit()

            rev_db = db.execute("SELECT revision FROM catalog_meta WHERE id=1").fetchone()[0]
            self.assertGreater(rev_db, rev_before, "SQLite trigger must bump catalog_meta revision on product update.")

            # Reading from store again updates cache automatically
            store.select()
            self.assertEqual(store.revision, rev_db, "CatalogStore must refresh its cache to match DB revision.")

    # --- Test 11: Production Dataset Validation (40-50 Products, 5 Categories, Stock & Images) ---
    def test_11_production_dataset_verification(self):
        prod_db_path = Path(__file__).parent / "instance" / "ecommerce.db"
        if not prod_db_path.exists():
            self.skipTest("Production database ecommerce.db not present.")

        conn = sqlite3.connect(str(prod_db_path))
        conn.row_factory = sqlite3.Row

        # Check total product count (around 40-50)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        self.assertGreaterEqual(count, 40, f"Expected at least 40 products, found {count}.")

        # Check the 5 required categories
        cats = [row["name"] for row in conn.execute("SELECT name FROM categories").fetchall()]
        required_cats = ["Electronics", "Clothing", "Footwear", "Home and Kitchen", "Books and Stationery"]
        for req in required_cats:
            self.assertIn(req, cats, f"Required category '{req}' missing from database.")

        # Check normal stock, low stock (1-5), and zero stock (0)
        zero_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock=0").fetchone()[0]
        low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock > 0 AND stock <= 5").fetchone()[0]
        normal_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock > 5").fetchone()[0]

        self.assertGreater(zero_stock, 0, "Must have zero-stock examples.")
        self.assertGreater(low_stock, 0, "Must have low-stock (1-5) examples.")
        self.assertGreater(normal_stock, 0, "Must have normal-stock examples.")

        # Check local image existence
        products = conn.execute("SELECT id, image_path FROM products").fetchall()
        for p in products:
            img_rel = p["image_path"]
            img_file = Path(__file__).parent / "app" / "static" / img_rel
            self.assertTrue(img_file.exists(), f"Image file for product {p['id']} not found: {img_file}")

        conn.close()

    # --- Test 12: Feature Folder Architecture Validation ---
    def test_12_feature_folder_pattern(self):
        # 1. Verify app.features.__init__.py is loaded and blueprint is registered
        self.assertIn("inventory", self.app.blueprints, "Feature 'inventory' blueprint must be registered.")

        # 2. Verify inventory feature index endpoint
        res = self.client.get("/inventory/")
        self.assertEqual(res.status_code, 200, "Feature route /inventory/ must return HTTP 200.")
        self.assertIn("Inventory management", res.text)

        # 3. Verify feature route for edit
        with self.app.app_context():
            db = get_db()
            row = db.execute("SELECT id FROM products WHERE name='Updated Wireless Mouse Pro'").fetchone()
            pid = row["id"]

        edit_res = self.client.get(f"/inventory/products/{pid}/edit")
        self.assertEqual(edit_res.status_code, 200, "Feature edit route must return HTTP 200.")
        self.assertIn("Edit product", edit_res.text)


if __name__ == "__main__":
    unittest.main()
