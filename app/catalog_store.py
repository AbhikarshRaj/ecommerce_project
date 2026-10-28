"""A hash-map catalog with set indexes, rebuilt only after data changes."""
from threading import RLock
from .database import get_db


class CatalogStore:
    def __init__(self):
        self.lock = RLock()
        self.revision = -1
        self.products = {}
        self.by_category = {}
        self.by_subcategory = {}
        self.active_ids = set()

    def _ensure_fresh(self, db):
        started_tx = False
        if not db.in_transaction:
            db.execute("BEGIN")
            started_tx = True
        try:
            version = db.execute("SELECT revision FROM catalog_meta WHERE id=1").fetchone()[0]
            if version != self.revision:
                rows = db.execute("""SELECT p.*, c.name AS category,
                    COALESCE(s.name,'') AS subcategory
                    FROM products p JOIN categories c ON c.id=p.category_id
                    LEFT JOIN subcategories s ON s.id=p.subcategory_id
                    ORDER BY p.created_at DESC, p.rowid DESC""").fetchall()
                products, categories, subcategories, active_ids = {}, {}, {}, set()
                for row in rows:
                    product = dict(row)
                    # Normalize is_active to 1 if not present
                    product["is_active"] = int(product.get("is_active", 1))
                    pid = product["id"]
                    products[pid] = product
                    if product["is_active"]:
                        active_ids.add(pid)
                    categories.setdefault(product["category_id"], set()).add(pid)
                    if product["subcategory_id"] is not None:
                        subcategories.setdefault(product["subcategory_id"], set()).add(pid)
                self.products = products
                self.by_category = categories
                self.by_subcategory = subcategories
                self.active_ids = active_ids
                self.revision = version
            if started_tx:
                db.commit()
        except Exception:
            if started_tx:
                db.rollback()
            raise

    def get(self, product_id):
        """O(1) dictionary lookup for a single product by ID."""
        with self.lock:
            db = get_db()
            self._ensure_fresh(db)
            product = self.products.get(product_id)
            return dict(product) if product else None

    def select(self, category=None, subcategory=None, query="", active_only=True):
        """Select products using category/subcategory sets and dictionary lookup.

        When active_only=True (default for customer storefront), inactive products
        are excluded using the active_ids index.
        When active_only=False, all products (including inactive) are returned.
        """
        with self.lock:
            db = get_db()
            self._ensure_fresh(db)

            ids = None
            if active_only:
                # Start candidate set from active products index
                if category is not None:
                    ids = self.by_category.get(category, set()) & self.active_ids
                if subcategory is not None:
                    subset = self.by_subcategory.get(subcategory, set()) & self.active_ids
                    ids = subset if ids is None else ids & subset
                if ids is None:
                    candidates = [p for p in self.products.values() if p["id"] in self.active_ids]
                else:
                    candidates = [self.products[i] for i in ids]
            else:
                if category is not None:
                    ids = self.by_category.get(category, set())
                if subcategory is not None:
                    subset = self.by_subcategory.get(subcategory, set())
                    ids = subset if ids is None else ids & subset
                candidates = list(self.products.values()) if ids is None else [self.products[i] for i in ids]

            # Substring search is still a linear scan of the candidate products.
            query = query.strip().casefold()
            if query:
                candidates = [p for p in candidates if query in p["name"].casefold()]

            # Stable display order for set-based results; costs O(k log k).
            if ids is not None:
                candidates.sort(key=lambda p: (p["name"].casefold(), p["id"]))

            return {p["id"]: dict(p) for p in candidates}
