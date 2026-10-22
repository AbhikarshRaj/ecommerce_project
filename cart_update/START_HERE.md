# MarketLane — Shopping cart milestone

Install this after the previous admin catalog update. It adds product-card Add to cart and plus/minus controls, a dedicated cart page, editable quantities, item removal, clear-cart confirmation, live totals and badge, and persistent undo/redo.

## Installation

1. Stop Flask with Ctrl+C.
2. Extract the ZIP and place `cart_update` beside `run.py` inside `ecommerce_project`.
3. In your project terminal, activate `.venv` if needed and run:

```powershell
.\.venv\Scripts\Activate.ps1
python .\cart_update\install_cart.py
python run.py
```

No new Python dependency is required beyond the existing Flask/Pillow setup.

4. Hard-refresh the browser with Ctrl+F5. Visit http://127.0.0.1:5000/ and http://127.0.0.1:5000/cart.

The installer checks the expected admin-update files before writing and backs up changed files in `backup_before_cart_<timestamp>`. It refuses duplicate installation or existing conflicting cart modules. If it stops because a section is different, send the error; do not bypass the checks.

The installer preserves your products, categories, images, admin password, homepage styling, banner carousel, and search. It adds a `shopping_carts` table automatically when Flask next starts. It does not drop or clear existing tables. Admin login/logout now preserves the browser's cart identity.

## How to use

- Click Add to cart on a product card. It becomes a minus / quantity / plus control.
- Plus adds one unit, subject to live stock and the per-item limit.
- Minus subtracts one. At quantity 1, minus removes the item.
- The cart badge counts total units, not distinct products.
- Open Cart in the header to view line totals and the subtotal.
- On the cart page, type a whole quantity directly and leave the field to save. Zero removes the item.
- Remove deletes one item. Clear cart asks for confirmation before removing all items.
- Undo reverses the most recent cart change. Redo reapplies it.
- A new ordinary edit clears the redo branch.
- A clear-cart action is one undoable operation; all affected quantities are restored together, if current stock allows.
- Latest 100 undoable actions are retained, with oldest actions discarded when full. The recent-changes list shows the active undo history, not a permanent operational audit log.
- A cart can contain up to 100 distinct products and up to 999 units of each, also limited by stock.

## Try this locally

1. Add a product twice and check that the badge shows 2 and only one cart row exists.
2. Click minus: quantity and badge become 1.
3. Click minus again: the product is removed.
4. Click Undo: quantity 1 is restored. Click Redo: it is removed again.
5. Add two different products. Verify each line total equals price × quantity, and the subtotal equals the sum of line totals.
6. Clear the cart and then Undo. Both items should return.
7. Reload the browser and restart Flask: quantities and undo/redo should remain.
8. Open an incognito browser: it should have a separate cart.
9. Try a product with stock 0: adding is disabled. Try exceeding available stock: the server rejects it.
10. Use a narrow browser window and check that the cart summary moves below the items.

The checkout button is explicitly disabled. Ordering, stock deduction, delivery charges, additional taxes, payment, and FIFO order routing are the next milestone. Prices/availability are read from current products when the cart loads. Adding to a cart does not reserve or reduce stock.

## Persistence and browser identity

SQLite stores the cart and both histories. A random cart identifier is stored in Flask's signed browser session cookie; raw cart contents are not stored in the cookie. The cookie lasts up to 30 days and is renewed during use. Keep the same browser cookie and `instance/session.key` to reconnect to the saved cart after restarting Flask. Clearing cookies, using another browser, or losing the session key creates a different cart. This is a guest-cart design; there is no customer login or cross-device cart synchronization yet.

Two tabs share the same cart. Every mutation supplies a revision number. If another tab changed the cart first, the server returns the latest state and asks the user to retry rather than silently overwriting it. Returning focus to the window refreshes the cart. Idle tabs do not poll continuously. Network failures do not automatically retry writes; reload to check whether a request was saved before repeating it.

Undo/redo validates live stock before restoring quantities. If stock has fallen, a restoration may be rejected and its history entry remains available. Undo/redo restores quantities, not historical prices. All prices and totals come from the server; browser-submitted prices are ignored.

## Files added

| File | Responsibility |
|---|---|
| `app/cart.py` | Cart routes, SQLite persistence, stock validation, totals, revision checks |
| `app/bounded_stack.py` | Custom fixed-capacity LIFO stack implemented using a circular array |
| `app/templates/cart.html` | Dedicated cart page and clear-cart dialog |
| `app/templates/_cart_controls.html` | Product-card Add / plus / minus controls |
| `app/static/css/cart.css` | Separate cart styling and responsive layouts |
| `app/static/js/cart.js` | Button requests, cart rendering, badge, messages and focus handling |

Existing `__init__.py`, `admin.py`, `catalog.html`, `_product_cards.html`, and `home.js` receive small integration changes. After installation, edit the real files under `app`, not the copies under `cart_update/payload`.

## Python DSA and complexity

The cart is represented as a Python dictionary:

```python
items = {'P101': 2, 'P102': 1}
```

Lookup/update/removal by ID has average O(1) cost for the underlying dictionary. A mutation uses a working dictionary copy for validation, which costs O(c) for c distinct cart products. Rendering, calculating totals, and serializing the cart also take O(c), excluding string lengths and database work.

Undo and redo each use a custom `BoundedStack` with a fixed list buffer, start index, and size. Push/pop/peek take O(1). When full, push overwrites the oldest bottom entry and advances the start index. No shifting of all elements is required. The latest action is still popped first (LIFO).

An action stores quantity changes, for example:

```python
{'changes': {'P101': {'before': 1, 'after': 2}},
 'label': 'Wireless Mouse: 1 → 2'}
```

A normal edit pushes onto undo and resets redo. Undo transfers the latest undo action to redo while applying `before` values; redo transfers it back while applying `after` values. Clear-cart stores one batch of c changes and validates restoration atomically.

For durable storage, every request restores the dictionaries/stacks from JSON in SQLite, and every write serializes the updated state. Therefore the ENTIRE HTTP operation is NOT O(1). It includes O(c + H) data processing, where H is the total number of product-change entries retained in both histories, plus SQL and response work. A history entry can contain c changes after clear-cart. Both stack entry counts and cart item counts are bounded, keeping local-project memory predictable. SQLite's `BEGIN IMMEDIATE` serializes writes and prevents lost read-modify-write updates. This correctness-first persistent design is suitable for the laptop project; higher-scale systems could use normalized history rows or an incremental cache.

This milestone implements real Python dictionary and stack usage. It does not implement the order-processing queue or a permanent operational log yet.

## Verification performed

The isolated Python checks cover bounded-stack wraparound and empty behavior; add/increase/decrease/set/remove/clear; subtotal calculations; invalid quantities and out-of-stock rejection; undo/redo and redo invalidation; stock changes blocking restoration; current-price use; CSRF enforcement; separate browser identities; stale revisions; application restart with retained cookie; admin login/logout preserving cart; and bounded history under repeated interaction.

JavaScript syntax was checked. A browser-layout test could not run because the test browser download failed; use the local interaction checklist above to check the appearance in your browser.

Optional: after installing, run isolated checks without changing your live data:

```powershell
python .\cart_update\check_cart.py
```

The test script copies the app into a temporary directory with a separate database and synthetic products; it does not access your real database or product images.
