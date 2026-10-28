"""Routes and request validation for the Inventory feature (Task 1).

Follows the MarketLane feature folder convention:
app/features/inventory/
  __init__.py Blueprint export
  routes.py URLs and request validation
  services.py Business logic
"""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from app.database import get_db
from app.admin import login_required
from . import services

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def get_taxonomy():
    db = get_db()
    categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY name COLLATE NOCASE")]
    subcategories = [dict(r) for r in db.execute("SELECT * FROM subcategories ORDER BY name COLLATE NOCASE")]
    return categories, subcategories


@inventory_bp.get("/")
@login_required
def index():
    """Inventory overview listing."""
    categories, subcategories = get_taxonomy()
    products = current_app.extensions["catalog_store"].select(active_only=False)
    return render_template("inventory/index.html",
                           products=products,
                           categories=categories,
                           subcategories=subcategories)


@inventory_bp.route("/products/<product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    """Edit product details, manage stock, toggle active status, and replace image."""
    db = get_db()
    product = services.fetch_product(db, product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.dashboard"))

    categories, subcategories = get_taxonomy()

    if request.method == "POST":
        try:
            upload = request.files.get("image")
            name = services.update_product_details(
                db=db,
                product_id=product_id,
                form_data=request.form,
                image_upload=upload,
                upload_folder=current_app.config["UPLOAD_FOLDER"]
            )
            flash(f"'{name}' was updated successfully.", "success")
            return redirect(url_for("admin.dashboard"))
        except (ValueError, Exception) as error:
            flash(str(error) if isinstance(error, ValueError) else "Could not update the product.", "error")
            product_values = dict(product)
            product_values.update(request.form.to_dict())
            if "price" in request.form:
                try:
                    product_values["price_paise"] = services.parse_price_paise(request.form["price"])
                except Exception:
                    pass
            if "stock" in request.form:
                try:
                    product_values["stock"] = int(request.form["stock"])
                except Exception:
                    pass
            product_values["is_active"] = 1 if request.form.get("is_active") in {"1", "true", "on"} else 0
            return render_template("inventory/edit.html",
                                   product=product_values,
                                   categories=categories,
                                   subcategories=subcategories), 400

    return render_template("inventory/edit.html",
                           product=product,
                           categories=categories,
                           subcategories=subcategories)


@inventory_bp.post("/products/<product_id>/activate")
@login_required
def activate_product(product_id):
    """Activate product to make it visible on the storefront."""
    db = get_db()
    try:
        name = services.set_active_status(db, product_id, 1)
        flash(f"'{name}' has been activated and is now visible on the storefront.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.dashboard"))


@inventory_bp.post("/products/<product_id>/deactivate")
@login_required
def deactivate_product(product_id):
    """Deactivate product to exclude it from storefront browsing and purchasing."""
    db = get_db()
    try:
        name = services.set_active_status(db, product_id, 0)
        flash(f"'{name}' has been deactivated and hidden from customers.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.dashboard"))


@inventory_bp.post("/products/<product_id>/toggle-status")
@login_required
def toggle_status(product_id):
    """Toggle between active and inactive status."""
    db = get_db()
    try:
        name, new_status = services.toggle_status(db, product_id)
        action_text = "activated and is now visible on storefront" if new_status else "deactivated and hidden from customers"
        flash(f"'{name}' was {action_text}.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.dashboard"))


@inventory_bp.post("/products/<product_id>/restock")
@login_required
def restock_product(product_id):
    """Quickly update stock quantity."""
    db = get_db()
    try:
        name, new_stock = services.set_product_stock(db, product_id, request.form.get("stock"))
        flash(f"Stock for '{name}' updated to {new_stock}.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.dashboard"))
