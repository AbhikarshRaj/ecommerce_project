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


def dashboard_context(values=None):
    db = get_db()
    return dict(
        categories=[dict(r) for r in db.execute("SELECT * FROM categories ORDER BY name COLLATE NOCASE")],
        subcategories=[dict(r) for r in db.execute("SELECT * FROM subcategories ORDER BY name COLLATE NOCASE")],
        products=current_app.extensions["catalog_store"].select(),
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
        raw_price = request.form.get("price", "").strip()
        if len(raw_price) > 20:
            raise ValueError("Enter a valid price.")
        try:
            price = Decimal(raw_price)
            if not price.is_finite() or price < 0 or price > 10_000_000:
                raise ValueError("Price must be between ₹0 and ₹1,00,00,000.")
            paise = price * 100
            if paise != paise.to_integral_value():
                raise ValueError("Price can have at most two decimal places.")
        except InvalidOperation:
            raise ValueError("Enter a valid price, such as 799.50.") from None
        raw_stock = request.form.get("stock", "").strip()
        if not raw_stock.isascii() or not raw_stock.isdigit() or len(raw_stock) > 7 or int(raw_stock) > 1_000_000:
            raise ValueError("Stock must be a whole number between 0 and 1,000,000.")
        image_path, image_file = save_image(request.files.get("image"))
        pid = "P-" + uuid.uuid4().hex
        db = get_db()
        # One transaction: an invalid product never leaves a new category behind.
        with db:
            parent = category_id(db, category)
            child = subcategory_id(db, parent, subcategory)
            db.execute("""INSERT INTO products
                (id,name,category_id,subcategory_id,price_paise,stock,image_path)
                VALUES (?,?,?,?,?,?,?)""",
                (pid, name, parent, child, int(paise), int(raw_stock), image_path))
    except (ValueError, sqlite3.Error, OSError) as error:
        if image_file:
            image_file.unlink(missing_ok=True)
        if not isinstance(error, ValueError):
            current_app.logger.exception("Product save failed")
        flash(str(error) if isinstance(error, ValueError) else "Could not save the product. Please try again.", "error")
        return render_template("admin_catalog.html", **dashboard_context(request.form.to_dict())), 400
    flash(f"{name} was added. It is now available on the storefront.", "success")
    return redirect(url_for("admin.dashboard"))
