"""Business logic for catalog and inventory management (Task 1).

Encapsulates validation, image processing, database updates, and stock adjustments.
"""
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
import sqlite3
import unicodedata
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from app.database import clean_name, category_id, subcategory_id


def parse_price_paise(raw_price):
    raw_price = (raw_price or "").strip()
    if len(raw_price) > 20:
        raise ValueError("Enter a valid price.")
    try:
        price = Decimal(raw_price)
        if not price.is_finite() or price < 0 or price > 10_000_000:
            raise ValueError("Price must be between ₹0 and ₹1,00,00,000.")
        paise = price * 100
        if paise != paise.to_integral_value():
            raise ValueError("Price can have at most two decimal places.")
        return int(paise)
    except InvalidOperation:
        raise ValueError("Enter a valid price, such as 799.50.") from None


def parse_stock(raw_stock):
    raw_stock = (raw_stock or "").strip()
    if not raw_stock.isascii() or not raw_stock.isdigit() or len(raw_stock) > 7 or int(raw_stock) > 1_000_000:
        raise ValueError("Stock must be a whole number between 0 and 1,000,000.")
    return int(raw_stock)


def validated_field(value, field_name, required=True, maximum=80):
    val = clean_name(value or "")
    if (required and not val) or len(val) > maximum:
        raise ValueError(f"{field_name.title()} must contain {'1' if required else '0'}–{maximum} characters.")
    return val


def save_product_image(upload, upload_folder):
    """Validate, thumbnail-optimize, and store an uploaded product image."""
    if not upload or not upload.filename:
        raise ValueError("Choose a product image.")
    raw = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("The image must be no larger than 5 MB.")
    try:
        with Image.open(BytesIO(raw)) as probe:
            if probe.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Choose a JPEG, PNG, or WebP image.")
            if probe.width * probe.height > 20_000_000:
                raise ValueError("Choose an image with at most 20 million pixels.")
            if getattr(probe, "n_frames", 1) != 1:
                raise ValueError("Choose a still image, not an animated image.")
            probe.verify()
        with Image.open(BytesIO(raw)) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source).convert("RGBA")
            oriented.thumbnail((1600, 1600))
            output = Image.new("RGB", oriented.size, "white")
            output.paste(oriented, mask=oriented.getchannel("A"))
            filename = uuid.uuid4().hex + ".jpg"
            path = Path(upload_folder) / filename
            try:
                output.save(path, "JPEG", quality=88, optimize=True)
            except Exception:
                path.unlink(missing_ok=True)
                raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("The image could not be read. Choose a valid JPEG, PNG, or WebP image.") from error
    return f"uploads/products/{filename}", path


def fetch_product(db, product_id):
    """Retrieve product with category and subcategory names."""
    row = db.execute("""SELECT p.*, c.name AS category,
        COALESCE(s.name, '') AS subcategory
        FROM products p
        JOIN categories c ON c.id=p.category_id
        LEFT JOIN subcategories s ON s.id=p.subcategory_id
        WHERE p.id=?""", (product_id,)).fetchone()
    return dict(row) if row else None


def update_product_details(db, product_id, form_data, image_upload, upload_folder):
    """Apply validated updates to product attributes, handling optional image replacement."""
    product = fetch_product(db, product_id)
    if not product:
        raise ValueError("Product not found.")

    name = validated_field(form_data.get("name"), "Product name", maximum=120)
    category = validated_field(form_data.get("category"), "Category")
    subcategory = validated_field(form_data.get("subcategory"), "Subcategory", required=False)
    paise = parse_price_paise(form_data.get("price"))
    stock = parse_stock(form_data.get("stock"))
    is_active = 1 if form_data.get("is_active") in {"1", "true", "on"} else 0

    new_image_file = None
    if image_upload and image_upload.filename:
        image_path, new_image_file = save_product_image(image_upload, upload_folder)
    else:
        image_path = product["image_path"]

    try:
        with db:
            parent = category_id(db, category)
            child = subcategory_id(db, parent, subcategory)
            db.execute("""UPDATE products SET
                name=?, category_id=?, subcategory_id=?, price_paise=?,
                stock=?, image_path=?, is_active=?
                WHERE id=?""",
                (name, parent, child, paise, stock, image_path, is_active, product_id))
    except Exception:
        if new_image_file:
            new_image_file.unlink(missing_ok=True)
        raise

    return name


def set_active_status(db, product_id, status_val):
    """Explicitly activate (1) or deactivate (0) a product."""
    product = db.execute("SELECT id, name FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        raise ValueError("Product not found.")
    with db:
        db.execute("UPDATE products SET is_active=? WHERE id=?", (int(status_val), product_id))
    return product["name"]


def toggle_status(db, product_id):
    """Toggle product active status between active and inactive."""
    product = db.execute("SELECT id, name, is_active FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        raise ValueError("Product not found.")
    new_status = 0 if product["is_active"] else 1
    with db:
        db.execute("UPDATE products SET is_active=? WHERE id=?", (new_status, product_id))
    return product["name"], new_status


def set_product_stock(db, product_id, raw_stock):
    """Directly update product inventory stock."""
    product = db.execute("SELECT id, name FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        raise ValueError("Product not found.")
    new_stock = parse_stock(raw_stock)
    with db:
        db.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
    return product["name"], new_stock
