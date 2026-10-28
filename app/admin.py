"""Local admin login, taxonomy creation, and validated image/product uploads."""
from decimal import Decimal, InvalidOperation
from functools import wraps
from io import BytesIO
from pathlib import Path
import secrets
import sqlite3
import uuid
import click
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .database import get_db, clean_name, category_id, subcategory_id

admin = Blueprint("admin", __name__, url_prefix="/admin")


def setting(key):
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        revision = setting("admin_revision")
        if not revision or session.get("admin_revision") != revision:
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapper


def register_commands(app):
    @app.cli.command("set-admin-password")
    @click.password_option(confirmation_prompt=True)
    def set_password(password):
        """Set the local administrator password without putting it in source code."""
        if len(password) < 10:
            raise click.ClickException("Use at least 10 characters.")
        db = get_db()
        with db:
            db.execute("INSERT OR REPLACE INTO settings VALUES ('admin_password',?)",
                       (generate_password_hash(password),))
            db.execute("INSERT OR REPLACE INTO settings VALUES ('admin_revision',?)",
                       (secrets.token_hex(24),))
        click.echo("Administrator password saved. Sign in at /admin/login.")


@admin.route("/login", methods=["GET", "POST"])
def login():
    configured = setting("admin_password")
    if request.method == "POST":
        password = request.form.get("password", "")
        if configured and check_password_hash(configured, password):
            saved_cart_id = session.get('cart_id')
            session.clear()
            if saved_cart_id:
                session['cart_id'] = saved_cart_id
                session.permanent = True
            session["admin_revision"] = setting("admin_revision")
            return redirect(url_for("admin.dashboard"))
        flash("Incorrect password or administrator not configured.", "error")
        return render_template("admin_login.html", configured=bool(configured)), 401
    return render_template("admin_login.html", configured=bool(configured))


@admin.post("/logout")
def logout():
    saved_cart_id = session.get('cart_id')
    session.clear()
    if saved_cart_id:
        session['cart_id'] = saved_cart_id
        session.permanent = True
    return redirect(url_for("catalog"))


def validated_name(field, required=True, maximum=80):
    value = clean_name(request.form.get(field, ""))
    if (required and not value) or len(value) > maximum:
        raise ValueError(f"{field.replace('_', ' ').title()} must contain {'1' if required else '0'}–{maximum} characters.")
    return value


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


def save_image(upload):
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
            # Flatten transparent pixels onto white, strip metadata and re-encode.
            output = Image.new("RGB", oriented.size, "white")
            output.paste(oriented, mask=oriented.getchannel("A"))
            filename = uuid.uuid4().hex + ".jpg"
            path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
            try:
                output.save(path, "JPEG", quality=88, optimize=True)
            except Exception:
                path.unlink(missing_ok=True)
                raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("The image could not be read. Choose a valid JPEG, PNG, or WebP image.") from error
    return f"uploads/products/{filename}", path


def get_taxonomy():
    db = get_db()
    categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY name COLLATE NOCASE")]
    subcategories = [dict(r) for r in db.execute("SELECT * FROM subcategories ORDER BY name COLLATE NOCASE")]
    return categories, subcategories


def dashboard_context(values=None):
    categories, subcategories = get_taxonomy()
    # Admin dashboard displays all products (both active and inactive)
    products = current_app.extensions["catalog_store"].select(active_only=False)
    return dict(
        categories=categories,
        subcategories=subcategories,
        products=products,
        values=values or {},
    )


@admin.get("/")
@login_required
def dashboard():
    return render_template("admin_catalog.html", **dashboard_context())


@admin.post("/taxonomy")
@login_required
def add_taxonomy():
    try:
        category = validated_name("category")
        subcategory = validated_name("subcategory", required=False)
        db = get_db()
        with db:
            parent = category_id(db, category)
            subcategory_id(db, parent, subcategory)
        flash("Category/subcategory is ready. Existing names were reused.", "success")
    except (ValueError, sqlite3.Error) as error:
        if isinstance(error, sqlite3.Error):
            current_app.logger.exception("Taxonomy save failed")
        flash(str(error) if isinstance(error, ValueError) else "Could not save. Please try again.", "error")
    return redirect(url_for("admin.dashboard"))


@admin.post("/products")
@login_required
def add_product():
    image_file = None
    try:
        name = validated_name("name", maximum=120)
        category = validated_name("category")
        subcategory = validated_name("subcategory", required=False)
        paise = parse_price_paise(request.form.get("price"))
        stock = parse_stock(request.form.get("stock"))
        is_active = 1 if request.form.get("is_active", "1") in {"1", "true", "on"} else 0
        image_path, image_file = save_image(request.files.get("image"))
        pid = "P-" + uuid.uuid4().hex
        db = get_db()
        with db:
            parent = category_id(db, category)
            child = subcategory_id(db, parent, subcategory)
            db.execute("""INSERT INTO products
                (id,name,category_id,subcategory_id,price_paise,stock,image_path,is_active)
                VALUES (?,?,?,?,?,?,?,?)""",
                (pid, name, parent, child, paise, stock, image_path, is_active))
    except (ValueError, sqlite3.Error, OSError) as error:
        if image_file:
            image_file.unlink(missing_ok=True)
        if not isinstance(error, ValueError):
            current_app.logger.exception("Product save failed")
        flash(str(error) if isinstance(error, ValueError) else "Could not save the product. Please try again.", "error")
        return render_template("admin_catalog.html", **dashboard_context(request.form.to_dict())), 400
    flash(f"{name} was added. It is now available on the storefront.", "success")
    return redirect(url_for("admin.dashboard"))


def fetch_product_details(product_id):
    db = get_db()
    row = db.execute("""SELECT p.*, c.name AS category,
        COALESCE(s.name, '') AS subcategory
        FROM products p
        JOIN categories c ON c.id=p.category_id
        LEFT JOIN subcategories s ON s.id=p.subcategory_id
        WHERE p.id=?""", (product_id,)).fetchone()
    return dict(row) if row else None


@admin.route("/products/<product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = fetch_product_details(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))

    categories, subcategories = get_taxonomy()

    if request.method == "POST":
        new_image_file = None
        try:
            name = validated_name("name", maximum=120)
            category = validated_name("category")
            subcategory = validated_name("subcategory", required=False)
            paise = parse_price_paise(request.form.get("price"))
            stock = parse_stock(request.form.get("stock"))
            is_active = 1 if request.form.get("is_active") in {"1", "true", "on"} else 0

            # Optional replacement image: retain existing image if none uploaded
            upload = request.files.get("image")
            if upload and upload.filename:
                image_path, new_image_file = save_image(upload)
            else:
                image_path = product["image_path"]

            db = get_db()
            with db:
                parent = category_id(db, category)
                child = subcategory_id(db, parent, subcategory)
                db.execute("""UPDATE products SET
                    name=?, category_id=?, subcategory_id=?, price_paise=?,
                    stock=?, image_path=?, is_active=?
                    WHERE id=?""",
                    (name, parent, child, paise, stock, image_path, is_active, product_id))

            flash(f"'{name}' was updated successfully.", "success")
            return redirect(url_for("admin.dashboard"))
        except (ValueError, sqlite3.Error, OSError) as error:
            if new_image_file:
                new_image_file.unlink(missing_ok=True)
            if not isinstance(error, ValueError):
                current_app.logger.exception("Product update failed")
            flash(str(error) if isinstance(error, ValueError) else "Could not update the product. Please try again.", "error")
            # Populate form with submitted values for user correction
            product_values = dict(product)
            product_values.update(request.form.to_dict())
            if "price" in request.form:
                try:
                    product_values["price_paise"] = parse_price_paise(request.form["price"])
                except Exception:
                    pass
            if "stock" in request.form:
                try:
                    product_values["stock"] = int(request.form["stock"])
                except Exception:
                    pass
            product_values["is_active"] = 1 if request.form.get("is_active") in {"1", "true", "on"} else 0
            return render_template("admin_product_edit.html",
                                   product=product_values,
                                   categories=categories,
                                   subcategories=subcategories), 400

    # GET request
    return render_template("admin_product_edit.html",
                           product=product,
                           categories=categories,
                           subcategories=subcategories)


@admin.post("/products/<product_id>/activate")
@login_required
def activate_product(product_id):
    db = get_db()
    product = db.execute("SELECT id, name FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))
    with db:
        db.execute("UPDATE products SET is_active=1 WHERE id=?", (product_id,))
    flash(f"'{product['name']}' has been activated and is now visible on the storefront.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/products/<product_id>/deactivate")
@login_required
def deactivate_product(product_id):
    db = get_db()
    product = db.execute("SELECT id, name FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))
    with db:
        db.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))
    flash(f"'{product['name']}' has been deactivated and hidden from customers.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/products/<product_id>/toggle-status")
@login_required
def toggle_status(product_id):
    db = get_db()
    product = db.execute("SELECT id, name, is_active FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))
    new_status = 0 if product["is_active"] else 1
    with db:
        db.execute("UPDATE products SET is_active=? WHERE id=?", (new_status, product_id))
    action_text = "activated and is now visible on storefront" if new_status else "deactivated and hidden from customers"
    flash(f"'{product['name']}' was {action_text}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/products/<product_id>/restock")
@login_required
def restock_product(product_id):
    db = get_db()
    product = db.execute("SELECT id, name, stock FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))
    try:
        new_stock = parse_stock(request.form.get("stock"))
        with db:
            db.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
        flash(f"Stock for '{product['name']}' updated to {new_stock}.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.dashboard"))
