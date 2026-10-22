# MarketLane — Admin catalog milestone

This update adds SQLite persistence, administrator login, category/subcategory creation or reuse, validated product image uploads, price and stock entry, and storefront integration. It is built for the HTML/CSS/JS homepage supplied in our conversation. It is not a replacement standalone website.

## Install on Windows in VS Code

1. Stop the Flask server with Ctrl+C.
2. Extract the ZIP. Put the `admin_update` folder directly inside your existing `ecommerce_project` folder, next to `run.py`. Do not put it inside `app` or `.venv`.
3. Open a terminal in `ecommerce_project`. Activate your existing environment if needed:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Install the new dependency and apply the update:

```powershell
python -m pip install -r .\admin_update\requirements-admin.txt
python .\admin_update\install_update.py
```

The installer checks the earlier homepage's expected sections before changing any files. It backs up replaced files under `backup_before_admin_<timestamp>`. If it cannot locate those sections, it stops with an explanation; send that message rather than editing the installer to bypass the checks. It refuses a second install.

The installer preserves existing CSS (including your focus-outline fix), carousel code, banner images, and product images. It extracts the product dictionary from your existing `app/__init__.py` without executing it and saves it as `app/seed_products.json` for a one-time database import. It replaces `app/__init__.py` with the new application factory. This is designed for the current tutorial stage; if you have added unrelated Python routes, merge those from the backup afterward.

5. Choose an admin password of at least 10 characters:

```powershell
python -m flask --app run set-admin-password
```

Type the password and confirm it when prompted. Characters are intentionally not displayed in the terminal. The password is hashed in SQLite, not stored in source code. Running this command again changes the password and invalidates existing admin sessions.

6. Update your dependency list and start Flask:

```powershell
python -m pip freeze > requirements.txt
python run.py
```

7. Open http://127.0.0.1:5000/admin/ and sign in. Open http://127.0.0.1:5000/ for the storefront. Hard-refresh with Ctrl+F5 after installing the update. The footer also has an Admin link.

## First demonstration

- Product name: Wireless Headphones
- Category: Electronics (select a suggestion or type it)
- Subcategory: Headphones
- Price: 1499.00
- Stock: 10
- Image: a JPEG, PNG, or WebP image from your computer
- Click Save product; use View storefront to see it.

Add a second product using ` electronics ` and `HEADPHONES`. They reuse the existing category and subcategory. Add the same subcategory name under a different category and it creates a separate subcategory under that parent.

Use the right-hand form to create a category/subcategory without a product. Empty categories appear in navigation and show the empty state when selected. Subcategories are optional on products.

## What changes in the homepage

- Category buttons are generated from SQLite rather than a fixed HTML list.
- A subcategory dropdown appears above the cards.
- Saved product images use their stored path instead of assuming `<product_id>.jpg`.
- Product cards are generated through the `_product_cards.html` partial template.
- Search and filter requests go to `/api/catalog`; results update without reloading the page.
- A 200 ms search debounce reduces requests; older requests are cancelled.
- A failed request shows a retry message instead of claiming there are no products.
- Admin additions appear on the next homepage load or search/filter request. A homepage left idle in another tab does not poll automatically; refresh it to get new category navigation.
- Existing banner buttons find their named category. If it does not exist, they show all products.
- Cart functionality remains the existing placeholder.

## Data storage

- `instance/ecommerce.db`: categories, subcategories, products, catalog revision and administrator settings.
- `instance/session.key`: persistent session-signing secret.
- `app/static/uploads/products/`: newly uploaded product images, using generated unique filenames.
- `app/seed_products.json`: original sample catalog; imported only once.
- Original product images in `app/static/images/products/` and banner images are preserved.

Do not delete the database to restart the application. Restarting Flask preserves the catalog. Editing the old seed file after initial import will not change existing database records. Add new records through the admin page.

Back up the database AND uploaded images together when moving the project to another laptop. Do not share `session.key` or the real database with admin credentials as public source code. The current server is intended for local laptop evaluation using the existing loopback-bound `run.py`; public deployment needs separate configuration and login rate limiting.

## File responsibilities

| File | Role |
|---|---|
| `app/__init__.py` | App creation, homepage/API routes, configuration and CSRF checks |
| `app/database.py` | Schema, database connections, normalized taxonomy names, seed import |
| `app/catalog_store.py` | Python hash-map catalog and category/subcategory set indexes |
| `app/admin.py` | Login, password CLI, product validation, image handling and transactions |
| `app/templates/admin_base.html` | Shared admin header and feedback messages |
| `app/templates/admin_login.html` | Admin sign-in screen |
| `app/templates/admin_catalog.html` | Product and taxonomy forms, saved inventory |
| `app/templates/_product_cards.html` | Shared escaped product-card rendering |
| `app/static/css/admin.css` | Separate responsive admin stylesheet |
| `app/static/js/admin.js` | Image preview and dependent subcategory suggestions |
| Existing homepage files | Automatically patched integration; your design is retained |

The `payload` directory contains the readable source files copied by the installer. You can inspect them before installing. After installation, edit the actual files under `app`, not the copies under `admin_update/payload`.

## DSA used meaningfully

`CatalogStore` builds:

```python
products = {product_id: product_details}
by_category = {category_id: {product_id, ...}}
by_subcategory = {subcategory_id: {product_id, ...}}
```

Python supplies the underlying hash table and set implementations; these are not custom hash tables.

- Product lookup by ID: average O(1), assuming bounded key size.
- Category/subcategory set lookup: average O(1).
- Intersection of selected category/subcategory IDs: expected O(min(a, b)).
- Fetching the k matching product records: O(k) average.
- Alphabetical display order for filtered products: O(k log k).
- Substring search: scans the candidate records and compares text; cost depends on candidate count and string lengths. No trie yet.
- First use or a product change: O(n) rebuild of dictionary and set indexes, excluding SQL query/join/order costs.
- Cache space: O(n) records and memberships, assuming fixed-size record fields.
- Rendering k cards and transferring the results still requires work proportional to the result size.

The database revision is checked when reading the catalog. SQLite triggers increment it on product insert/update/delete, so cached indexes refresh after changes, including when another application instance writes. An RLock protects each process's cache, and a SQLite read transaction keeps each rebuild internally consistent. The initial catalog is loaded on demand.

The SQL uniqueness constraint on normalized category names prevents duplicates. Subcategory uniqueness is scoped to its parent category. A composite foreign key prevents a product from referencing a subcategory belonging to another category. These are database integrity rules, distinct from our in-memory DSA indexes.

## Validation and boundaries

- Names are trimmed, whitespace is collapsed, and Unicode compatibility normalization plus case folding is used for category matching.
- Price is parsed using Decimal and stored as integer paise, with at most two decimal places and a range of 0 to 10,000,000 rupees.
- Stock must be a whole number between 0 and 1,000,000. Zero stock displays as out of stock.
- Image: at most 5 MB, 20 million pixels, one still frame, JPEG/PNG/WebP.
- Image contents are decoded and re-encoded to JPEG; filenames are generated, dimensions are reduced to at most 1600×1600, and transparent areas become white.
- SQLite transactions save the category, subcategory and product together. Handled database failures remove a newly written image. An abrupt machine/process crash between filesystem and database operations can still leave an orphan image; they are separate storage systems.
- Sign-in and write forms have CSRF tokens. Product names are escaped by Jinja.
- Successful writes redirect to avoid browser refresh resubmitting the same POST. A deliberate second submission adds a distinct product; products with identical names are allowed and have separate IDs.
- Product editing/deletion, stock adjustments, cart, checkout, undo/redo, logs, and trie search are later milestones.

## Verification

Run optional isolated integration checks:

```powershell
python .\admin_update\check_update.py
```

These build a temporary test project and never edit your live database. They cover installer preservation/duplicate-install guard, admin login/CSRF, category reuse, parent-scoped subcategories, image saving/serving, filtering, invalid input, HTML escaping, restart persistence and logout. They do not constitute a browser screenshot/layout test of your actual local site.

## Troubleshooting

- `No module named PIL`: install requirements using the same activated Python environment.
- Missing-template or installer-anchor errors: check that the homepage files contain the earlier supplied code and are saved as UTF-8.
- Old category buttons/CSS after installation: Ctrl+F5, and confirm the running server is this project.
- Expired form: refresh the admin page and submit again. If validation fails, reselect the image.
- Database already exists with a different schema: back it up and ask for a migration; do not delete it blindly.

Implementation references:
- https://flask.palletsprojects.com/en/stable/tutorial/database/
- https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
- https://pillow.readthedocs.io/en/stable/reference/Image.html
- https://pillow.readthedocs.io/en/stable/reference/ImageOps.html
