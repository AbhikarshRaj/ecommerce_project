"""Seed script for Task 1: Populates 50 realistic products with local images across 5 categories.

Categories:
1. Electronics
2. Clothing
3. Footwear
4. Home and Kitchen
5. Books and Stationery

Stock distribution includes normal-stock, low-stock (1-5), and zero-stock examples.
Usable local images are generated and saved under app/static/images/products/.
"""
import json
from pathlib import Path
import sqlite3
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
STATIC_IMG_DIR = BASE_DIR / "app" / "static" / "images" / "products"
SEED_FILE = BASE_DIR / "app" / "seed_products.json"
DB_PATH = BASE_DIR / "instance" / "ecommerce.db"

PRODUCTS_DATA = [
    # --- Electronics (10 products) ---
    {
        "id": "P101",
        "name": "Wireless Ergonomic Mouse",
        "category": "Electronics",
        "subcategory": "Computer Accessories",
        "price_paise": 129900,
        "stock": 24,
        "is_active": 1,
        "symbol": "🖱️"
    },
    {
        "id": "P102",
        "name": "Mechanical Gaming Keyboard",
        "category": "Electronics",
        "subcategory": "Computer Accessories",
        "price_paise": 299900,
        "stock": 12,
        "is_active": 1,
        "symbol": "⌨️"
    },
    {
        "id": "P103",
        "name": "Ultra HD 4K Pro Webcam",
        "category": "Electronics",
        "subcategory": "Computer Accessories",
        "price_paise": 349900,
        "stock": 3,
        "is_active": 1,
        "symbol": "📷"
    },
    {
        "id": "P104",
        "name": "Noise-Cancelling Headphones",
        "category": "Electronics",
        "subcategory": "Audio & Headphones",
        "price_paise": 449900,
        "stock": 18,
        "is_active": 1,
        "symbol": "🎧"
    },
    {
        "id": "P105",
        "name": "True Wireless Earbuds",
        "category": "Electronics",
        "subcategory": "Audio & Headphones",
        "price_paise": 189900,
        "stock": 0,
        "is_active": 1,
        "symbol": "🎵"
    },
    {
        "id": "P106",
        "name": "Portable Bluetooth Speaker",
        "category": "Electronics",
        "subcategory": "Audio & Headphones",
        "price_paise": 219900,
        "stock": 8,
        "is_active": 1,
        "symbol": "🔊"
    },
    {
        "id": "P107",
        "name": "65W GaN Fast Charger",
        "category": "Electronics",
        "subcategory": "Mobile Accessories",
        "price_paise": 119900,
        "stock": 30,
        "is_active": 1,
        "symbol": "⚡"
    },
    {
        "id": "P108",
        "name": "Braided USB-C Fast Cable",
        "category": "Electronics",
        "subcategory": "Mobile Accessories",
        "price_paise": 49900,
        "stock": 5,
        "is_active": 1,
        "symbol": "🔌"
    },
    {
        "id": "P109",
        "name": "AMOLED Fitness Smartwatch",
        "category": "Electronics",
        "subcategory": "Smart Wearables",
        "price_paise": 329900,
        "stock": 15,
        "is_active": 1,
        "symbol": "⌚"
    },
    {
        "id": "P110",
        "name": "Magnetic 10000mAh Power Bank",
        "category": "Electronics",
        "subcategory": "Mobile Accessories",
        "price_paise": 169900,
        "stock": 0,
        "is_active": 0,  # Deactivated sample
        "symbol": "🔋"
    },

    # --- Clothing (10 products) ---
    {
        "id": "P111",
        "name": "Classic Crewneck Cotton Tee",
        "category": "Clothing",
        "subcategory": "Men's Apparel",
        "price_paise": 69900,
        "stock": 40,
        "is_active": 1,
        "symbol": "👕"
    },
    {
        "id": "P112",
        "name": "Slim Fit Stretch Denim Jeans",
        "category": "Clothing",
        "subcategory": "Men's Apparel",
        "price_paise": 179900,
        "stock": 18,
        "is_active": 1,
        "symbol": "👖"
    },
    {
        "id": "P113",
        "name": "Linen Casual Button-Down Shirt",
        "category": "Clothing",
        "subcategory": "Men's Apparel",
        "price_paise": 149900,
        "stock": 2,
        "is_active": 1,
        "symbol": "👔"
    },
    {
        "id": "P114",
        "name": "Floral Wrap Summer Blouse",
        "category": "Clothing",
        "subcategory": "Women's Apparel",
        "price_paise": 99900,
        "stock": 20,
        "is_active": 1,
        "symbol": "👗"
    },
    {
        "id": "P115",
        "name": "High-Waist Tailored Trousers",
        "category": "Clothing",
        "subcategory": "Women's Apparel",
        "price_paise": 159900,
        "stock": 11,
        "is_active": 1,
        "symbol": "✨"
    },
    {
        "id": "P116",
        "name": "Cozy Oversized Fleece Hoodie",
        "category": "Clothing",
        "subcategory": "Casual Wear",
        "price_paise": 189900,
        "stock": 0,
        "is_active": 1,
        "symbol": "🧥"
    },
    {
        "id": "P117",
        "name": "All-Weather Windbreaker Jacket",
        "category": "Clothing",
        "subcategory": "Outerwear",
        "price_paise": 249900,
        "stock": 9,
        "is_active": 1,
        "symbol": "🌬️"
    },
    {
        "id": "P118",
        "name": "French Terry Sports Joggers",
        "category": "Clothing",
        "subcategory": "Casual Wear",
        "price_paise": 119900,
        "stock": 4,
        "is_active": 1,
        "symbol": "🏃"
    },
    {
        "id": "P119",
        "name": "Merino Wool Blend Sweater",
        "category": "Clothing",
        "subcategory": "Outerwear",
        "price_paise": 229900,
        "stock": 14,
        "is_active": 1,
        "symbol": "🧶"
    },
    {
        "id": "P120",
        "name": "Vintage Acid-Wash Graphic Tee",
        "category": "Clothing",
        "subcategory": "Casual Wear",
        "price_paise": 79900,
        "stock": 0,
        "is_active": 0,  # Deactivated sample
        "symbol": "🎨"
    },

    # --- Footwear (10 products) ---
    {
        "id": "P121",
        "name": "Performance Road Running Shoes",
        "category": "Footwear",
        "subcategory": "Athletic Footwear",
        "price_paise": 299900,
        "stock": 22,
        "is_active": 1,
        "symbol": "👟"
    },
    {
        "id": "P122",
        "name": "Canvas Low-Top Sneakers",
        "category": "Footwear",
        "subcategory": "Casual Sneakers",
        "price_paise": 149900,
        "stock": 25,
        "is_active": 1,
        "symbol": "👟"
    },
    {
        "id": "P123",
        "name": "Retro Leather Court Sneakers",
        "category": "Footwear",
        "subcategory": "Casual Sneakers",
        "price_paise": 239900,
        "stock": 3,
        "is_active": 1,
        "symbol": "👟"
    },
    {
        "id": "P124",
        "name": "Derby Leather Formal Shoes",
        "category": "Footwear",
        "subcategory": "Formal Shoes",
        "price_paise": 349900,
        "stock": 10,
        "is_active": 1,
        "symbol": "👞"
    },
    {
        "id": "P125",
        "name": "Suede Handcrafted Penny Loafers",
        "category": "Footwear",
        "subcategory": "Formal Shoes",
        "price_paise": 279900,
        "stock": 0,
        "is_active": 1,
        "symbol": "👞"
    },
    {
        "id": "P126",
        "name": "Waterproof Trail Hiking Boots",
        "category": "Footwear",
        "subcategory": "Outdoor Footwear",
        "price_paise": 389900,
        "stock": 7,
        "is_active": 1,
        "symbol": "🥾"
    },
    {
        "id": "P127",
        "name": "Cloud-Cushion Recovery Slides",
        "category": "Footwear",
        "subcategory": "Sandals & Slides",
        "price_paise": 89900,
        "stock": 35,
        "is_active": 1,
        "symbol": "🩴"
    },
    {
        "id": "P128",
        "name": "Chelsea Leather Ankle Boots",
        "category": "Footwear",
        "subcategory": "Boots",
        "price_paise": 319900,
        "stock": 1,
        "is_active": 1,
        "symbol": "👢"
    },
    {
        "id": "P129",
        "name": "Breathable Slip-On Walkers",
        "category": "Footwear",
        "subcategory": "Casual Sneakers",
        "price_paise": 169900,
        "stock": 16,
        "is_active": 1,
        "symbol": "👟"
    },
    {
        "id": "P130",
        "name": "Dual-Strap Cork Footbed Sandals",
        "category": "Footwear",
        "subcategory": "Sandals & Slides",
        "price_paise": 129900,
        "stock": 12,
        "is_active": 1,
        "symbol": "👡"
    },

    # --- Home and Kitchen (10 products) ---
    {
        "id": "P131",
        "name": "Cast Iron Skillet 10-inch",
        "category": "Home and Kitchen",
        "subcategory": "Cookware",
        "price_paise": 189900,
        "stock": 16,
        "is_active": 1,
        "symbol": "🍳"
    },
    {
        "id": "P132",
        "name": "Damascus Steel Chef Knife 8-in",
        "category": "Home and Kitchen",
        "subcategory": "Kitchen Tools",
        "price_paise": 219900,
        "stock": 20,
        "is_active": 1,
        "symbol": "🔪"
    },
    {
        "id": "P133",
        "name": "Borosilicate Glass Water Bottle",
        "category": "Home and Kitchen",
        "subcategory": "Drinkware",
        "price_paise": 59900,
        "stock": 38,
        "is_active": 1,
        "symbol": "🍶"
    },
    {
        "id": "P134",
        "name": "Stainless Steel Travel Tumbler",
        "category": "Home and Kitchen",
        "subcategory": "Drinkware",
        "price_paise": 89900,
        "stock": 4,
        "is_active": 1,
        "symbol": "🥤"
    },
    {
        "id": "P135",
        "name": "6-Piece Glass Storage Set",
        "category": "Home and Kitchen",
        "subcategory": "Storage & Containers",
        "price_paise": 139900,
        "stock": 14,
        "is_active": 1,
        "symbol": "📦"
    },
    {
        "id": "P136",
        "name": "Bamboo Chopping Board Set",
        "category": "Home and Kitchen",
        "subcategory": "Kitchen Tools",
        "price_paise": 79900,
        "stock": 0,
        "is_active": 1,
        "symbol": "🪵"
    },
    {
        "id": "P137",
        "name": "Stainless Steel French Press",
        "category": "Home and Kitchen",
        "subcategory": "Drinkware",
        "price_paise": 119900,
        "stock": 9,
        "is_active": 1,
        "symbol": "☕"
    },
    {
        "id": "P138",
        "name": "Precision Burr Manual Grinder",
        "category": "Home and Kitchen",
        "subcategory": "Kitchen Tools",
        "price_paise": 159900,
        "stock": 2,
        "is_active": 1,
        "symbol": "⚙️"
    },
    {
        "id": "P139",
        "name": "Matte Ceramic Ribbed Vase",
        "category": "Home and Kitchen",
        "subcategory": "Home Decor",
        "price_paise": 74900,
        "stock": 20,
        "is_active": 1,
        "symbol": "🏺"
    },
    {
        "id": "P140",
        "name": "Ultrasonic Aroma Diffuser",
        "category": "Home and Kitchen",
        "subcategory": "Home Decor",
        "price_paise": 149900,
        "stock": 11,
        "is_active": 1,
        "symbol": "🌸"
    },

    # --- Books and Stationery (10 products) ---
    {
        "id": "P141",
        "name": "Hardcover Dotted Grid Journal",
        "category": "Books and Stationery",
        "subcategory": "Notebooks & Journals",
        "price_paise": 39900,
        "stock": 45,
        "is_active": 1,
        "symbol": "📓"
    },
    {
        "id": "P142",
        "name": "Brass Fine Fountain Pen",
        "category": "Books and Stationery",
        "subcategory": "Writing Instruments",
        "price_paise": 89900,
        "stock": 15,
        "is_active": 1,
        "symbol": "✒️"
    },
    {
        "id": "P143",
        "name": "Quick-Dry Gel Pens (Pack of 6)",
        "category": "Books and Stationery",
        "subcategory": "Writing Instruments",
        "price_paise": 34900,
        "stock": 55,
        "is_active": 1,
        "symbol": "🖊️"
    },
    {
        "id": "P144",
        "name": "Solid Wood Desk Organizer",
        "category": "Books and Stationery",
        "subcategory": "Desk Accessories",
        "price_paise": 99900,
        "stock": 5,
        "is_active": 1,
        "symbol": "🗄️"
    },
    {
        "id": "P145",
        "name": "Pastel Highlighters (Pack of 8)",
        "category": "Books and Stationery",
        "subcategory": "Writing Instruments",
        "price_paise": 27900,
        "stock": 0,
        "is_active": 1,
        "symbol": "🖍️"
    },
    {
        "id": "P146",
        "name": "Watercolor Sketchbook 300 GSM",
        "category": "Books and Stationery",
        "subcategory": "Art & Craft",
        "price_paise": 64900,
        "stock": 19,
        "is_active": 1,
        "symbol": "🎨"
    },
    {
        "id": "P147",
        "name": "Wire Mesh Document Sorter",
        "category": "Books and Stationery",
        "subcategory": "Desk Accessories",
        "price_paise": 49900,
        "stock": 25,
        "is_active": 1,
        "symbol": "📁"
    },
    {
        "id": "P148",
        "name": "Self-Healing Cutting Mat A3",
        "category": "Books and Stationery",
        "subcategory": "Art & Craft",
        "price_paise": 74900,
        "stock": 3,
        "is_active": 1,
        "symbol": "📐"
    },
    {
        "id": "P149",
        "name": "Minimalist Weekly Goal Planner",
        "category": "Books and Stationery",
        "subcategory": "Notebooks & Journals",
        "price_paise": 44900,
        "stock": 28,
        "is_active": 1,
        "symbol": "📅"
    },
    {
        "id": "P150",
        "name": "Aluminum Laptop Riser Stand",
        "category": "Books and Stationery",
        "subcategory": "Desk Accessories",
        "price_paise": 129900,
        "stock": 0,
        "is_active": 0,  # Deactivated sample
        "symbol": "💻"
    }
]

CATEGORY_PALETTES = {
    "Electronics": {
        "bg": (24, 38, 56),        # Slate Navy
        "card": (255, 255, 255),
        "primary": (23, 94, 76),     # Brand green
        "accent": (56, 189, 248),    # Sky cyan
        "text": (23, 44, 40)
    },
    "Clothing": {
        "bg": (68, 40, 29),        # Warm Terracotta
        "card": (255, 255, 255),
        "primary": (180, 83, 9),     # Amber
        "accent": (251, 146, 60),    # Orange
        "text": (23, 44, 40)
    },
    "Footwear": {
        "bg": (20, 60, 48),        # Forest Green
        "card": (255, 255, 255),
        "primary": (23, 94, 76),     # Brand green
        "accent": (52, 211, 153),    # Mint
        "text": (23, 44, 40)
    },
    "Home and Kitchen": {
        "bg": (76, 29, 45),        # Deep Burgundy
        "card": (255, 255, 255),
        "primary": (190, 24, 93),    # Rose
        "accent": (244, 114, 182),   # Pink
        "text": (23, 44, 40)
    },
    "Books and Stationery": {
        "bg": (35, 39, 70),        # Deep Indigo
        "card": (255, 255, 255),
        "primary": (79, 70, 229),    # Indigo
        "accent": (167, 139, 250),   # Violet
        "text": (23, 44, 40)
    }
}


def generate_local_images():
    STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
    size = (400, 400)

    for item in PRODUCTS_DATA:
        pid = item["id"]
        cat = item["category"]
        palette = CATEGORY_PALETTES.get(cat, CATEGORY_PALETTES["Electronics"])

        img = Image.new("RGB", size, palette["bg"])
        draw = ImageDraw.Draw(img)

        # Draw outer subtle border
        draw.rectangle([10, 10, 390, 390], outline=palette["accent"], width=2)

        # Inner card
        card_box = [28, 28, 372, 372]
        draw.rounded_rectangle(card_box, radius=18, fill=palette["card"], outline=(220, 229, 222), width=1)

        # Top Category badge
        draw.rounded_rectangle([44, 42, 356, 74], radius=8, fill=(240, 246, 242))
        cat_badge_text = f"MARKETLANE · {cat.upper()}"
        draw.text((200, 58), cat_badge_text, fill=palette["primary"], anchor="mm")

        # Center illustration decorative box
        draw.rounded_rectangle([70, 95, 330, 245], radius=14, fill=(248, 250, 248), outline=(225, 235, 228), width=1)
        
        # Center symbol/label representation
        first_letter = item["name"][0]
        # Decorative circle in center
        draw.ellipse([150, 125, 250, 225], fill=palette["primary"])
        draw.text((200, 175), first_letter, fill=(255, 255, 255), anchor="mm")

        # Subcategory tag
        sub = item["subcategory"]
        draw.text((200, 265), sub, fill=(99, 115, 107), anchor="mm")

        # Product name (multi-line wrap if long)
        name = item["name"]
        if len(name) > 28:
            parts = name.split()
            mid = len(parts) // 2
            line1 = " ".join(parts[:mid])
            line2 = " ".join(parts[mid:])
            draw.text((200, 292), line1, fill=palette["text"], anchor="mm")
            draw.text((200, 312), line2, fill=palette["text"], anchor="mm")
        else:
            draw.text((200, 302), name, fill=palette["text"], anchor="mm")

        # Bottom price & stock row
        price_rupees = f"₹{item['price_paise'] // 100}"
        draw.text((60, 345), price_rupees, fill=palette["primary"], anchor="lm")

        stock = item["stock"]
        if stock == 0:
            stock_label = "Out of stock"
            badge_color = (220, 38, 38)
        elif stock <= 5:
            stock_label = f"Only {stock} left"
            badge_color = (180, 83, 9)
        else:
            stock_label = f"{stock} in stock"
            badge_color = (22, 101, 52)
        draw.text((340, 345), stock_label, fill=badge_color, anchor="rm")

        output_path = STATIC_IMG_DIR / f"{pid}.jpg"
        img.save(output_path, "JPEG", quality=90, optimize=True)

    print(f"Generated {len(PRODUCTS_DATA)} local product images in {STATIC_IMG_DIR}")


def save_seed_json():
    seed_dict = {}
    for item in PRODUCTS_DATA:
        seed_dict[item["id"]] = {
            "name": item["name"],
            "category": item["category"],
            "subcategory": item["subcategory"],
            "price_paise": item["price_paise"],
            "stock": item["stock"],
            "is_active": item["is_active"],
            "image_path": f"images/products/{item['id']}.jpg"
        }
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        json.dump(seed_dict, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(seed_dict)} products to {SEED_FILE}")


def populate_database():
    if not DB_PATH.exists():
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    with conn:
        for item in PRODUCTS_DATA:
            cat_name = item["category"].strip()
            cat_norm = cat_name.casefold()
            conn.execute("INSERT OR IGNORE INTO categories(name, normalized_name) VALUES (?, ?)", (cat_name, cat_norm))
            cat_id = conn.execute("SELECT id FROM categories WHERE normalized_name=?", (cat_norm,)).fetchone()["id"]

            sub_name = item["subcategory"].strip()
            sub_norm = sub_name.casefold()
            conn.execute("INSERT OR IGNORE INTO subcategories(category_id, name, normalized_name) VALUES (?, ?, ?)",
                         (cat_id, sub_name, sub_norm))
            sub_id = conn.execute("SELECT id FROM subcategories WHERE category_id=? AND normalized_name=?",
                                  (cat_id, sub_norm)).fetchone()["id"]

            img_path = f"images/products/{item['id']}.jpg"
            conn.execute("""
                INSERT INTO products (id, name, category_id, subcategory_id, price_paise, stock, image_path, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    category_id=excluded.category_id,
                    subcategory_id=excluded.subcategory_id,
                    price_paise=excluded.price_paise,
                    stock=excluded.stock,
                    image_path=excluded.image_path,
                    is_active=excluded.is_active
            """, (item["id"], item["name"], cat_id, sub_id, item["price_paise"], item["stock"], img_path, item["is_active"]))

        conn.execute("UPDATE catalog_meta SET revision = revision + 1 WHERE id=1")

    # Verify counts
    cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    prod_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    active_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0]
    conn.close()

    print(f"Database successfully populated! Total products: {prod_count} (Active: {active_count}), Categories: {cat_count}")


if __name__ == "__main__":
    generate_local_images()
    save_seed_json()
    populate_database()
