# MarketLane — Task 1: Catalog and Inventory

This repository contains the complete implementation of **Task 1: Catalog and Inventory** for the MarketLane Flask e-commerce system, adhering strictly to the architecture, feature folder conventions, and data structure requirements documented in the project plan.

---

## Table of Contents
1. [Overview & Deliverables](#overview--deliverables)
2. [Folder Structure Compliance Check](#folder-structure-compliance-check)
3. [Summary of Changes & Additions](#summary-of-changes--additions)
4. [Detailed Implementation of Task 1 Steps (1–9)](#detailed-implementation-of-task-1-steps-19)
5. [Data Structures & Algorithms (DSA) Explanation](#data-structures--algorithms-dsa-explanation)
6. [Team Handoff Specifications (Members 2, 3, 4, 5)](#team-handoff-specifications)
7. [Setup, Execution & Verification](#setup-execution--verification)
8. [Automated Test Suite (12 Tests)](#automated-test-suite-12-tests)

---

## Overview & Deliverables

- **Task Assigned:** Task 1: Catalog and inventory
- **Owner:** Member 1
- **Goal:** Administrator can edit, restock, and deactivate products; customers see the current active catalog on the storefront and search results; inactive products are excluded from shopping and blocked from purchase.

---

## Folder Structure Compliance Check

The project completion plan (Page 2) defines the shared architectural pattern for adding new features while preserving core systems:

```
New feature folder pattern:
app/features/<feature_name>/
  __init__.py Blueprint export
  routes.py URLs and request validation
  services.py Business logic
app/templates/<feature_name>/
  index.html
app/static/css/<feature_name>.css
app/static/js/<feature_name>.js # Only if needed

Guideline:
Create app/features/__init__.py once. Register each blueprint inside create_app(), 
before returning app. Existing admin, catalog and cart modules can stay where they are. 
Edit live application files, not installer payload copies.
```

### Verification & Compliance Matrix

| Required Convention | Implemented File / Path | Status | Purpose / Non-Disturbance Assurance |
| :--- | :--- | :---: | :--- |
| `app/features/__init__.py` | [`app/features/__init__.py`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/features/__init__.py) | **CONFIRMED** | Created once; contains `register_features(app)` which registers `inventory_bp` and dynamically auto-registers any future blueprints created by other teammates without modifying core files. |
| `app/features/<feature>/__init__.py` | [`app/features/inventory/__init__.py`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/features/inventory/__init__.py) | **CONFIRMED** | Exports `inventory_bp`. |
| `app/features/<feature>/routes.py` | [`app/features/inventory/routes.py`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/features/inventory/routes.py) | **CONFIRMED** | Encapsulates URLs and HTTP request validation for product editing, restocking, deactivation, and activation. |
| `app/features/<feature>/services.py` | [`app/features/inventory/services.py`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/features/inventory/services.py) | **CONFIRMED** | Encapsulates all inventory business logic: decimal price conversion, image processing with Pillow, stock updates, and database transactions. |
| `app/templates/<feature>/index.html` | [`app/templates/inventory/index.html`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/templates/inventory/index.html) | **CONFIRMED** | Feature-specific inventory overview template. Also includes [`app/templates/inventory/edit.html`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/templates/inventory/edit.html). |
| `app/static/css/<feature>.css` | [`app/static/css/inventory.css`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/static/css/inventory.css) | **CONFIRMED** | Feature stylesheet for badges, table layouts, action buttons, and edit grids. |
| `create_app()` registration | [`app/__init__.py`](file:///c:/Users/rutup/OneDrive/Desktop/dsa%20project%20copy/ecommerce_project/app/__init__.py) | **CONFIRMED** | Invokes `register_features(app)` directly before returning `app`. |
| Existing modules preserved | `app/admin.py`, `app/cart.py`, `app/catalog_store.py`, `app/database.py` | **CONFIRMED** | Unbroken backward compatibility. Existing routes (`/admin/`, `/admin/products/...`) and data access patterns remain fully functional. |

---

## Summary of Changes & Additions

### 1. Files Added
| File Path | Description / Purpose |
| :--- | :--- |
| `app/features/__init__.py` | Feature coordinator: automatically imports and registers all feature blueprints with the Flask application. |
| `app/features/inventory/__init__.py` | Feature blueprint export (`inventory_bp`). |
| `app/features/inventory/routes.py` | Request validation & routing for product edit, activate, deactivate, and restock actions. |
| `app/features/inventory/services.py` | Core business logic: price parsing in paise, stock checks, thumbnail optimization via Pillow, and atomic database updates. |
| `app/templates/inventory/index.html` | Feature-level inventory panel. |
| `app/templates/inventory/edit.html` | Feature-level product edit interface. |
| `app/templates/admin_product_edit.html` | Admin product edit template ensuring seamless backward compatibility with existing admin links. |
| `app/static/css/inventory.css` | Inventory feature stylesheet for status badges, image previews, and form layouts. |
| `app/static/images/products/*.jpg` | 50 local offline 400x400 JPEG product images generated with Pillow. |
| `migrate_task1.py` | Standalone migration script: creates timestamped backups of `ecommerce.db`, adds `is_active` column (default 1), and adds index `products_active`. |
| `seed_catalog.py` | Script generating the 50 local product images and seeding 50 realistic products across 5 categories in `seed_products.json` and SQLite. |
| `test_task1.py` | Automated test suite with 12 unit and integration tests verifying all steps of Task 1 and feature architecture. |
| `.gitignore` | Excludes `__pycache__`, compiled `.pyc` files, local virtual environments, test databases, and OS metadata. |

### 2. Files Modified
| File Path | Key Changes Made |
| :--- | :--- |
| `app/database.py` | • Added `is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))` to `SCHEMA`.<br>• Added index `CREATE INDEX IF NOT EXISTS products_active ON products(is_active)`.<br>• Added automatic self-migration inside `initialize()` for existing databases.<br>• Updated seed importer to preserve subcategories and `is_active` flags. |
| `app/catalog_store.py` | • Added `self.active_ids = set()` for in-memory active product indexing.<br>• Added `get(product_id)` for $\mathcal{O}(1)$ product dictionary lookup.<br>• Added `active_only=True` default parameter to `select()` so customer views and API queries automatically exclude inactive products.<br>• Safe transaction handling (`if not db.in_transaction: db.execute("BEGIN")`) during revision verification. |
| `app/cart.py` | • Updated `snapshot()`: checks `is_active`; if inactive, sets `unavailable = True` and `stock = 0`, prompting the cart UI to display `"Unavailable. Remove this item."` and disable incrementing.<br>• Updated `apply_changes()`: rejects adding, incrementing, or restoring deactivated products with `404 Not Found` (`"This product is no longer available. Remove it from your cart."`). |
| `app/admin.py` | • Product editing, status toggling, and restocking endpoints invoke `app.features.inventory.services`.<br>• Optional replacement image logic: retains original `image_path` if no replacement is uploaded.<br>• Updated `dashboard_context()` to pass `active_only=False` so administrators see all products. |
| `app/templates/admin_catalog.html` | • Added thumbnail image, stock badge, and status badge columns.<br>• Added "Edit" and "Activate / Deactivate" action buttons to each row.<br>• Added inventory summary counts (Total, Active, Inactive).<br>• Added client-side real-time filter search and status tabs (`All`, `Active`, `Inactive`, `Low / Out of stock`). |
| `app/static/css/admin.css` | • Added CSS rules for status badges (`.status-active`, `.status-inactive`), stock badges (`.in-stock`, `.low-stock`, `.out-of-stock`), action buttons (`.edit-btn`, `.activate-btn`, `.deactivate-btn`), and table thumbnails. |
| `app/seed_products.json` | • Expanded dataset from 6 initial products to 50 curated products spanning 5 categories with varying stock levels. |
| `requirements.txt` | • Standardized encoding to UTF-8 and added `Pillow>=10.0.0` for image validation and processing. |
| `run.py` | • Normalized `sys.path` so the application can be run directly from any directory. |

---

## Detailed Implementation of Task 1 Steps (1–9)

### Step 1: Review Existing Product Form, Database Fields & Validation
- **Existing Fields:** `id` (UUID), `name`, `category_id`, `subcategory_id`, `price_paise`, `stock`, `image_path`, `created_at`.
- **Validation Preserved & Extended:**
  - Name: Normalized with Unicode NFKC, stripped of excess whitespace, length 1–120 characters.
  - Price: Parsed with `decimal.Decimal`, checked finite, non-negative, $\le 10,000,000$, maximum 2 decimal places, stored as integer paise.
  - Stock: Integer between $0$ and $1,000,000$.
  - Images: Restricted to JPEG, PNG, or WebP; maximum 5 MB; maximum 20 million pixels; single-frame still images only.

### Step 2: Add an Edit Action to Each Product in the Admin List
- In `app/templates/admin_catalog.html`, an **Actions** column was added with an **Edit** button for every product row linking to `/admin/products/<id>/edit`.
- Clicking "Edit" loads `admin_product_edit.html` pre-populated with the product's live data.

### Step 3: Allow Changes to Name, Category, Subcategory, Price and Stock
- The edit form accepts modifications to all core attributes:
  - Text fields for name, category, and subcategory with dynamic datalist auto-completion.
  - Formatted price input (rendered in Rupees, converted to integer paise on the server).
  - Stock quantity input allowing direct inventory adjustment / restocking.
- Executed inside an atomic SQLite write transaction (`with db:`).

### Step 4: Allow an Optional Replacement Image (Retain Original if None Supplied)
- In `services.update_product_details()`:
  ```python
  if image_upload and image_upload.filename:
      image_path, new_image_file = save_product_image(image_upload, upload_folder)
  else:
      image_path = product["image_path"]  # Original image retained
  ```
- The edit view displays the current image and filename so the administrator can verify the existing asset before deciding whether to replace it.

### Step 5: Add an `is_active` Field Through a Migration Preserving Existing Records
- Column definition: `is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))`.
- Index: `CREATE INDEX IF NOT EXISTS products_active ON products(is_active)`.
- Migration mechanism:
  - Script `migrate_task1.py` backs up `ecommerce.db` to `ecommerce.db.bak_<timestamp>` and applies `ALTER TABLE products ADD COLUMN is_active ...`.
  - Application factory in `database.py:initialize()` checks `PRAGMA table_info(products)` on startup and applies the migration automatically if missing.
  - Existing records are preserved with `is_active = 1`.

### Step 6: Add Activate/Deactivate Actions & Shopping/Purchase Protection
- **Admin Actions:**
  - Dedicated buttons in the admin table and edit page trigger `POST /admin/products/<id>/toggle-status` or `/activate` / `/deactivate`.
  - Flashes clear status notifications upon change.
- **Storefront & API Exclusion:**
  - `CatalogStore.select()` accepts `active_only=True` (default). Inactive products are completely omitted from `/` and `/api/catalog`.
  - Admin view passes `active_only=False` to display both active and inactive inventory.
- **Cart Protection:**
  - Adding an inactive product via `/api/cart/action` returns HTTP 404: `"This product is no longer available. Remove it from your cart."`.
  - If an active product in a user's cart is subsequently deactivated, `snapshot()` sets `unavailable: True`.
  - The cart interface flags the item with `"Unavailable. Remove this item."` and prevents quantity increments or purchase.

### Step 7: Ensure Catalog Indexes Refresh After Edits, Updates & Activation Changes
- SQLite triggers monitor the `products` table:
  ```sql
  CREATE TRIGGER IF NOT EXISTS product_update AFTER UPDATE ON products
  BEGIN UPDATE catalog_meta SET revision=revision+1 WHERE id=1; END;
  ```
- Any `UPDATE` (name, price, stock, active status) automatically increments `catalog_meta.revision`.
- On the next read, `CatalogStore` detects that the database revision differs from `self.revision` and rebuilds the in-memory indexes under `RLock` in an atomic snapshot.

### Step 8: Populate 40–50 Products Across 5 Categories
- Populated exactly **50 products** distributed evenly (10 per category) across:
  1. **Electronics** (Computer accessories, audio, wearables, charging)
  2. **Clothing** (Men's wear, women's wear, casual wear, outerwear)
  3. **Footwear** (Running, sneakers, formal, boots, sandals)
  4. **Home and Kitchen** (Cookware, cutlery, drinkware, storage, decor)
  5. **Books and Stationery** (Notebooks, pens, desk accessories, art supplies)
- Saved in `app/seed_products.json` and populated in `instance/ecommerce.db`.

### Step 9: Stock Level Coverage & Usable Local Offline Images
- **Stock Distribution:**
  - Normal stock: 35 products (10 to 55 units)
  - Low stock: 8 products (1 to 5 units — triggers `"Only X left"` badge in UI)
  - Zero stock: 7 products (0 units — triggers `"Out of stock"` badge in UI)
  - Inactive samples: 3 products (P110, P120, P150) pre-set with `is_active = 0` for immediate demonstration.
- **Local Offline Images:**
  - 50 JPEG images generated using Pillow in `app/static/images/products/<id>.jpg`.
  - Each image contains category-specific colorways, clean card styling, typography, and product identifiers, requiring zero external internet access.

---

## Data Structures & Algorithms (DSA) Explanation

The catalog utilizes a hybrid persistent relational database (SQLite) and an in-memory index store (`CatalogStore` in `app/catalog_store.py`) to balance persistence with fast lookups.

```
+-----------------------------------------------------------------------------------+
|                                   CatalogStore                                    |
|                                                                                   |
|  self.products         (Hash Map / Dict)       :  product_id -> product_dict      |
|  self.active_ids       (Hash Set)              :  { "P101", "P102", ... }         |
|  self.by_category      (Inverted Index / Dict) :  category_id -> { pid_1, ... }   |
|  self.by_subcategory   (Inverted Index / Dict) :  subcat_id   -> { pid_2, ... }   |
+-----------------------------------------------------------------------------------+
                                         ▲
                                         │ Atomic rebuild when revision != db.revision
+-----------------------------------------------------------------------------------+
|                                SQLite Persistence                                 |
|                                                                                   |
|  Table: products (id, name, price_paise, stock, image_path, is_active, ...)       |
|  Table: catalog_meta (id=1, revision=K)                                           |
|  Triggers: product_insert, product_update, product_delete -> revision = revision+1|
+-----------------------------------------------------------------------------------+
```

### 1. Hash Map for Product ID Lookup (`self.products`)
- **Structure:** Python dictionary mapping `product_id (str) -> product_record (dict)`.
- **Complexity:** $\mathcal{O}(1)$ average time complexity for retrieval, insertion, and key checks.
- **Justification:** Avoids repetitive SQLite disk I/O when resolving product details after set candidate selection or validating cart items.

### 2. Inverted Index with Hash Sets (`self.active_ids`, `self.by_category`, `self.by_subcategory`)
- **Structure:**
  - `self.active_ids`: `set[str]` containing IDs of all active products.
  - `self.by_category`: `dict[int, set[str]]` mapping category ID to matching product IDs.
  - `self.by_subcategory`: `dict[int, set[str]]` mapping subcategory ID to matching product IDs.
- **Complexity:**
  - Set membership: $\mathcal{O}(1)$ average.
  - Set intersection: $\mathcal{O}(\min(|A|, |B|))$ where $|A|$ and $|B|$ are sizes of the candidate sets.
- **Justification:** Multi-faceted filtering (category + subcategory + active status) is resolved via set intersection:
  $$\text{candidates} = \text{self.active\_ids} \cap \text{self.by\_category}[cat\_id] \cap \text{self.by\_subcategory}[subcat\_id]$$
  Inactive products are filtered in set-intersection time rather than scanning the full catalog.

### 3. Substring Search & Stable Sorting
- **Search:** Linear filter over the small candidate subset: $\mathcal{O}(k \cdot m)$ where $k$ is candidate count and $m$ is title length.
- **Sorting:** Python's Timsort: $\mathcal{O}(k \log k)$ using `(name.casefold(), id)` as a deterministic tiebreaker for pagination stability.

### 4. Cache Consistency & Monotonic Revision Counter
- **Mechanism:** Updating products via the admin interface or cart operations fires SQLite triggers (`product_update`, etc.) that increment `catalog_meta.revision`.
- Inside `with self.lock:`, `CatalogStore` compares `self.revision` to SQLite's revision. If out of sync, it performs a bulk reload in $\mathcal{O}(N)$ and updates `self.revision`.
- Subsequent reads cost $\mathcal{O}(1)$ to $\mathcal{O}(k \log k)$ completely in memory.

### Complexity Summary

| Operation | Data Structure Used | Time Complexity | Space Complexity |
| :--- | :--- | :--- | :--- |
| **Direct Product Lookup** | `self.products` (Hash Map) | $\mathcal{O}(1)$ avg | $\mathcal{O}(1)$ |
| **Category Candidate Resolution** | Set intersection (`active_ids & by_category`) | $\mathcal{O}(\min(\|A\|, \|B\|))$ | $\mathcal{O}(k)$ |
| **Name Substring Search** | Linear scan over candidates | $\mathcal{O}(k \cdot m)$ | $\mathcal{O}(k)$ |
| **Candidate Sorting** | Timsort (Name/Price + ID tiebreaker) | $\mathcal{O}(k \log k)$ | $\mathcal{O}(k)$ |
| **Cache Synchronization** | Full rebuild from SQLite on revision bump | $\mathcal{O}(N)$ | $\mathcal{O}(N)$ |

---

## Team Handoff Specifications

### Handoff to Member 2 (Homepage & Banners)
- Local product images are saved at `app/static/images/products/<id>.jpg` and served via `url_for('static', filename=product.image_path)`.
- Fallback placeholders exist in `_product_cards.html` (`product.name[0]`).

### Handoff to Member 3 (Search, Filters & Sorting)
- **Database Column:** `is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))`.
- **Active Rule:** Products are eligible for storefront search and filtering if and only if `is_active == 1`.
- **CatalogStore Usage:**
  - Call `catalog_store.select(category, subcategory, query)` (defaults to `active_only=True`).
  - Alternatively, access `catalog_store.active_ids` set directly to intersect with your price/stock candidate sets.
  - Admin queries should explicitly pass `active_only=False`.

### Handoff to Member 4 (Checkout & Saved Orders)
- **Checkout Availability Check:** Inside your checkout transaction, verify:
  ```python
  product = db.execute("SELECT stock, is_active FROM products WHERE id=?", (pid,)).fetchone()
  if not product or not product["is_active"]:
      raise CheckoutError(f"Product '{pid}' is no longer active.")
  if product["stock"] < quantity:
      raise CheckoutError(f"Insufficient stock for product '{pid}'.")
  ```
- **Stock Deduction:** Updating stock (`UPDATE products SET stock = stock - ? WHERE id = ?`) automatically triggers `product_update`, increments `catalog_meta.revision`, and refreshes the cache.

### Handoff to Member 5 (Operational Logs)
- Hook `record_event(db, event_type, entity_type, entity_id, details)` into `services.py` / `routes.py`:
  - `edit_product`: `event_type="PRODUCT_EDIT"`
  - `activate_product`: `event_type="PRODUCT_ACTIVATE"`
  - `deactivate_product`: `event_type="PRODUCT_DEACTIVATE"`
  - `restock_product`: `event_type="PRODUCT_RESTOCK"`

---

## Setup, Execution & Verification

### 1. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. Apply Database Migration
```powershell
python migrate_task1.py
```
*(Creates a timestamped backup before adding `is_active` to `instance/ecommerce.db`)*

### 3. Populate Seed Catalog & Images (Optional / Standalone)
```powershell
python seed_catalog.py
```

### 4. Configure Local Admin Password
```powershell
python -m flask --app run set-admin-password
```
*(Choose a password with at least 10 characters)*

### 5. Run the Application
```powershell
python run.py
```
- **Storefront:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Shopping Cart:** [http://127.0.0.1:5000/cart](http://127.0.0.1:5000/cart)
- **Admin Dashboard:** [http://127.0.0.1:5000/admin/](http://127.0.0.1:5000/admin/)
- **Inventory Feature Panel:** [http://127.0.0.1:5000/inventory/](http://127.0.0.1:5000/inventory/)

---

## Automated Test Suite (12 Tests)

Run the unit and integration test suite:

```powershell
python test_task1.py
```

### Test Coverage (12 Tests)
1. `test_01_schema_has_is_active`: Confirms `is_active` column exists with default constraint.
2. `test_02_add_product_and_initial_state`: Confirms product creation with validation and `is_active=1`.
3. `test_03_edit_product_fields`: Verifies edits to name, category, subcategory, price, and stock without image upload.
4. `test_04_edit_product_replacement_image`: Verifies optional replacement image upload and processing.
5. `test_05_deactivate_product_excludes_from_shopping`: Confirms deactivated items are excluded from `/` and `/api/catalog` but visible in `/admin/`.
6. `test_06_activate_product_restores_to_shopping`: Confirms activation immediately restores products to customer view.
7. `test_07_cart_rejects_inactive_product`: Confirms adding an inactive product returns HTTP 404.
8. `test_08_cart_snapshot_marks_unavailable`: Confirms items deactivated after adding to cart are flagged `unavailable: True`.
9. `test_09_quick_restock`: Verifies quick restock updates stock in SQLite and in-memory cache.
10. `test_10_index_consistency_and_revision_bump`: Verifies SQLite triggers increment revision and trigger cache rebuilds.
11. `test_11_production_dataset_verification`: Confirms 50+ products across 5 categories, stock levels (normal, low, zero), and local images exist on disk.
12. `test_12_feature_folder_pattern`: Verifies `inventory` blueprint is registered via `app.features`, and `/inventory/` endpoints operate properly.

```
............
----------------------------------------------------------------------
Ran 12 tests in 0.713s

OK
```
