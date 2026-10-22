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

    def select(self, category=None, subcategory=None, query=""):
        with self.lock:
            db = get_db()
            # Read revision and rows in one consistent SQLite snapshot.
            db.execute("BEGIN")
            try:
                version = db.execute("SELECT revision FROM catalog_meta WHERE id=1").fetchone()[0]
                if version != self.revision:
                    rows = db.execute("""SELECT p.*, c.name AS category,
                        COALESCE(s.name,'') AS subcategory
                        FROM products p JOIN categories c ON c.id=p.category_id
                        LEFT JOIN subcategories s ON s.id=p.subcategory_id
                        ORDER BY p.created_at DESC, p.rowid DESC""").fetchall()
                    products, categories, subcategories = {}, {}, {}
                    for row in rows:
                        product = dict(row)
                        pid = product["id"]
                        products[pid] = product
                        categories.setdefault(product["category_id"], set()).add(pid)
                        if product["subcategory_id"] is not None:
                            subcategories.setdefault(product["subcategory_id"], set()).add(pid)
                    self.products = products
                    self.by_category = categories
                    self.by_subcategory = subcategories
                    self.revision = version
                db.commit()
            except Exception:
                db.rollback()
                raise

            ids = None
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
