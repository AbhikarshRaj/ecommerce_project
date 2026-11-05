"""MarketLane Catalog Store

Indexed product search and filtering for the MarketLane catalogue.

Data structures:
- Hash maps: product records and attribute-to-product-ID indexes.
- Hash sets: fast membership checks and filter intersections.
- Inverted index: exact word lookup for product-name search.
- Trigram index: partial-word lookup for product-name search.
- Sorted price index: binary-search price-range filtering.

Indexes are rebuilt only when catalog_meta.revision changes.
"""

import re
from bisect import bisect_left, bisect_right
from threading import RLock

from .database import get_db


class CatalogStore:
    def __init__(self):
        self.lock = RLock()
        self.revision = -1

        # Main map: product ID -> complete product record.
        self.products = {}

        # Attribute indexes: normalized attribute value -> product IDs.
        self.by_category = {}
        self.by_subcategory = {}
        self.by_brand = {}
        self.by_colour = {}
        self.by_gender = {}
        self.by_size = {}
        self.by_material = {}
        self.by_token = {}
        self.by_trigram = {}
        self.product_tokens = {}

        # Stock indexes contain product IDs.
        self.in_stock_ids = set()
        self.out_of_stock_ids = set()

        # Sorted tuples: (price_paise, product_id).
        self.price_index = []
        self.price_keys = []

    # ---------------------------------------------------------
    # NORMALIZATION HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def normalize_search_text(value):
        """Lowercase text and retain only alphanumeric words."""
        return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))

    @staticmethod
    def normalize_attribute(value):
        """Normalize a filter value while retaining spaces between words."""
        return CatalogStore.normalize_search_text(value)

    @staticmethod
    def normalize_gender(gender):
        """Convert common gender labels to male, female, or unisex."""
        gender = CatalogStore.normalize_attribute(gender)
        if gender in ("men", "mens", "man", "male"):
            return "male"
        if gender in ("women", "womens", "woman", "female"):
            return "female"
        if gender == "unisex":
            return "unisex"
        return gender

    @staticmethod
    def create_trigrams(word):
        """Return unique three-character sequences from a word."""
        if len(word) < 3:
            return set()
        return {word[i:i + 3] for i in range(len(word) - 2)}

    @staticmethod
    def _add_to_index(index, value, product_id):
        """Add a product ID to an attribute's hash-set posting list."""
        normalized = CatalogStore.normalize_attribute(value)
        if normalized:
            index.setdefault(normalized, set()).add(product_id)

    # ---------------------------------------------------------
    # BUILD / REBUILD INDEXES
    # ---------------------------------------------------------

    def rebuild_indexes(self, rows, version):
        """Build all indexes locally, then replace the old indexes."""
        products = {}
        categories = {}
        subcategories = {}
        brands = {}
        colours = {}
        genders = {}
        sizes = {}
        materials = {}
        token_index = {}
        trigram_index = {}
        product_tokens = {}
        in_stock = set()
        out_of_stock = set()
        price_index = []

        for row in rows:
            product = dict(row)
            product_id = product["id"]
            products[product_id] = product

            categories.setdefault(product.get("category_id"), set()).add(product_id)
            if product.get("subcategory_id") is not None:
                subcategories.setdefault(product["subcategory_id"], set()).add(product_id)

            self._add_to_index(brands, product.get("brand"), product_id)
            self._add_to_index(colours, product.get("colour"), product_id)
            self._add_to_index(genders, self.normalize_gender(product.get("gender")), product_id)
            self._add_to_index(sizes, product.get("size"), product_id)
            self._add_to_index(materials, product.get("material"), product_id)

            try:
                stock = int(product.get("stock") or 0)
            except (TypeError, ValueError):
                stock = 0
            (in_stock if stock > 0 else out_of_stock).add(product_id)

            try:
                price = int(product.get("price_paise") or 0)
            except (TypeError, ValueError):
                price = 0
            price_index.append((price, product_id))

            normalized_name = self.normalize_search_text(product.get("name", ""))
            tokens = set(normalized_name.split())
            product_tokens[product_id] = tokens

            for token in tokens:
                token_index.setdefault(token, set()).add(product_id)
                for trigram in self.create_trigrams(token):
                    trigram_index.setdefault(trigram, set()).add(product_id)

        price_index.sort()

        # Atomic replacement: readers never see half-built indexes.
        self.products = products
        self.by_category = categories
        self.by_subcategory = subcategories
        self.by_brand = brands
        self.by_colour = colours
        self.by_gender = genders
        self.by_size = sizes
        self.by_material = materials
        self.by_token = token_index
        self.by_trigram = trigram_index
        self.product_tokens = product_tokens
        self.in_stock_ids = in_stock
        self.out_of_stock_ids = out_of_stock
        self.price_index = price_index
        self.price_keys = [price for price, _ in price_index]
        self.revision = version

    def _ensure_indexes_are_current(self):
        """Refresh cached indexes only if the database revision changed."""
        db = get_db()
        db.execute("BEGIN")
        try:
            version_row = db.execute(
                "SELECT revision FROM catalog_meta WHERE id = 1"
            ).fetchone()
            version = version_row[0] if version_row else 0

            if version != self.revision:
                rows = db.execute(
                    """
                    SELECT p.*, c.name AS category,
                           COALESCE(s.name, '') AS subcategory
                    FROM products p
                    JOIN categories c ON c.id = p.category_id
                    LEFT JOIN subcategories s ON s.id = p.subcategory_id
                    ORDER BY p.created_at DESC, p.rowid DESC
                    """
                ).fetchall()
                self.rebuild_indexes(rows, version)
            db.commit()
        except Exception:
            db.rollback()
            raise

    # ---------------------------------------------------------
    # PRODUCT-NAME SEARCH
    # ---------------------------------------------------------

    def find_word_matches(self, word):
        """Find product IDs containing a complete or partial name token."""
        if not word:
            return set()

        if len(word) < 3:
            matches = set()
            for token, product_ids in self.by_token.items():
                if word in token:
                    matches.update(product_ids)
            return matches

        trigram_sets = [
            self.by_trigram.get(trigram, set())
            for trigram in self.create_trigrams(word)
        ]
        if not trigram_sets or any(not ids for ids in trigram_sets):
            return set()

        trigram_sets.sort(key=len)
        matches = set(trigram_sets[0])
        for ids in trigram_sets[1:]:
            matches.intersection_update(ids)
            if not matches:
                return set()

        return {
            product_id for product_id in matches
            if any(word in token for token in self.product_tokens.get(product_id, set()))
        }

    # ---------------------------------------------------------
    # FILTERING HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _parse_price(value, parameter_name):
        """Validate a price bound expressed in rupees; return paise."""
        if value is None or value == "":
            return None
        try:
            amount = float(value)
            if amount < 0:
                raise ValueError
            return round(amount * 100)
        except (TypeError, ValueError):
            raise ValueError(f"{parameter_name} must be a non-negative number in rupees.")

    @staticmethod
    def _intersect(current_ids, new_ids):
        """Intersect postings, beginning with the smaller set when possible."""
        if current_ids is None:
            return set(new_ids)
        if len(current_ids) > len(new_ids):
            current_ids, new_ids = new_ids, current_ids
        return current_ids.intersection(new_ids)

    def _price_matches(self, min_price_paise=None, max_price_paise=None):
        """Use binary search to retrieve IDs within an inclusive price range."""
        low = 0 if min_price_paise is None else bisect_left(self.price_keys, min_price_paise)
        high = len(self.price_index) if max_price_paise is None else bisect_right(self.price_keys, max_price_paise)
        return {product_id for _, product_id in self.price_index[low:high]}

    # ---------------------------------------------------------
    # MAIN SELECT FUNCTION
    # ---------------------------------------------------------

    def select(
        self,
        category=None,
        subcategory=None,
        query="",
        brand=None,
        colour=None,
        gender=None,
        size=None,
        material=None,
        min_price=None,
        max_price=None,
        in_stock=None,
        sort_by=None,
    ):
        """Return products matching every supplied filter (AND logic).

        min_price and max_price are in rupees. Supported sort_by values:
        name_asc, price_asc, price_desc. Default ordering preserves the
        catalogue's existing order when no filter/search is supplied.
        """
        with self.lock:
            self._ensure_indexes_are_current()

            normalized_query = self.normalize_search_text(query)
            search_words = normalized_query.split()

            # Preserve the existing convenient search behaviour:
            # "men shirt" means Male + shirt; "women shirt" means Female + shirt.
            query_gender = None
            if "men" in search_words or "mens" in search_words:
                query_gender = "male"
                search_words = [w for w in search_words if w not in ("men", "mens")]
            elif "women" in search_words or "womens" in search_words:
                query_gender = "female"
                search_words = [w for w in search_words if w not in ("women", "womens")]
            elif "male" in search_words:
                query_gender = "male"
                search_words.remove("male")
            elif "female" in search_words:
                query_gender = "female"
                search_words.remove("female")

            # Collect all applicable posting sets, then intersect the
            # smallest sets first to reduce the amount of set work.
            postings = []
            if category is not None and category != "":
                postings.append(self.by_category.get(category, set()))
            if subcategory is not None and subcategory != "":
                postings.append(self.by_subcategory.get(subcategory, set()))

            attribute_filters = (
                (self.by_brand, brand),
                (self.by_colour, colour),
                (self.by_gender, gender if gender not in (None, "") else query_gender),
                (self.by_size, size),
                (self.by_material, material),
            )
            for index, value in attribute_filters:
                if value is not None and value != "":
                    normalized = self.normalize_gender(value) if index is self.by_gender else self.normalize_attribute(value)
                    postings.append(index.get(normalized, set()))

            if in_stock is not None and in_stock != "":
                wants_stock = str(in_stock).casefold() in ("1", "true", "yes", "in_stock", "available")
                postings.append(self.in_stock_ids if wants_stock else self.out_of_stock_ids)

            min_price_paise = self._parse_price(min_price, "min_price")
            max_price_paise = self._parse_price(max_price, "max_price")
            if min_price_paise is not None and max_price_paise is not None and min_price_paise > max_price_paise:
                raise ValueError("min_price cannot be greater than max_price.")
            if min_price_paise is not None or max_price_paise is not None:
                postings.append(self._price_matches(min_price_paise, max_price_paise))

            for word in search_words:
                postings.append(self.find_word_matches(word))

            if postings:
                postings.sort(key=len)
                product_ids = set(postings[0])
                for ids in postings[1:]:
                    product_ids.intersection_update(ids)
                    if not product_ids:
                        break
                candidates = [self.products[pid] for pid in product_ids if pid in self.products]
            else:
                candidates = list(self.products.values())

            # Sorting is applied after filtering, before pagination in the API.
            if sort_by == "price_asc":
                candidates.sort(key=lambda p: (int(p.get("price_paise") or 0), p["id"]))
            elif sort_by == "price_desc":
                candidates.sort(key=lambda p: (-int(p.get("price_paise") or 0), p["id"]))
            elif sort_by in ("name_asc", "alphabetical"):
                candidates.sort(key=lambda p: (str(p.get("name", "")).casefold(), p["id"]))
            elif postings:
                # Retain the previous behaviour for filtered/search results.
                candidates.sort(key=lambda p: (str(p.get("name", "")).casefold(), p["id"]))

            return {product["id"]: dict(product) for product in candidates}

    # ---------------------------------------------------------
    # DYNAMIC FILTER OPTIONS (FACETS)
    # ---------------------------------------------------------

    def get_filter_options(self, products=None):
        """Return distinct available filter values for the supplied products.

        Pass the result of select() to calculate options for the currently
        matching products. The API can later exclude the currently selected
        facet when calculating that facet's options, as standard shops do.
        """
        with self.lock:
            records = self.products if products is None else products
            values = {
                "brands": set(),
                "colours": set(),
                "genders": set(),
                "sizes": set(),
                "materials": set(),
            }
            for product in records.values():
                for key, column in (
                    ("brands", "brand"),
                    ("colours", "colour"),
                    ("genders", "gender"),
                    ("sizes", "size"),
                    ("materials", "material"),
                ):
                    value = product.get(column)
                    if value is not None and str(value).strip():
                        normalized = self.normalize_gender(value) if key == "genders" else str(value).strip()
                        values[key].add(normalized)
            return {key: sorted(items, key=str.casefold) for key, items in values.items()}


# Shared store instance used by the Flask application.
catalog_store = CatalogStore()
