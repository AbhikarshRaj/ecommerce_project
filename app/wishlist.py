"""Wishlist functionality for individual browser sessions."""

from flask import Blueprint, jsonify, render_template, request
from .database import get_db
from .cart import customer_id


wishlist = Blueprint("wishlist", __name__)


# --------------------------------------------------
# WISHLIST PAGE
# --------------------------------------------------

@wishlist.get("/wishlist")
def wishlist_page():
    return render_template("wishlist.html")


# --------------------------------------------------
# GET WISHLIST ITEMS
# --------------------------------------------------

@wishlist.get("/api/wishlist")
def get_wishlist():

    db = get_db()
    owner = customer_id()

    rows = db.execute(
        """
        SELECT
            p.id,
            p.name,
            p.price_paise,
            p.image_path,
            p.stock,
            p.brand,
            p.colour
        FROM wishlist_items w
        JOIN products p
            ON w.product_id = p.id
        WHERE w.customer_id = ?
          AND p.is_active = 1
        ORDER BY w.added_at DESC
        """,
        (owner,)
    ).fetchall()

    products = [dict(row) for row in rows]

    response = jsonify(
        success=True,
        products=products,
        count=len(products)
    )

    response.headers["Cache-Control"] = "no-store"

    return response


# --------------------------------------------------
# ADD OR REMOVE A PRODUCT FROM WISHLIST
# --------------------------------------------------

@wishlist.post("/api/wishlist")
def update_wishlist():

    db = get_db()
    owner = customer_id()

    action = request.form.get("action", "").strip()
    product_id = request.form.get("product_id", "").strip()

    # Validate the action.
    if action not in {"add", "remove"}:
        return jsonify(
            success=False,
            error="Invalid wishlist action."
        ), 400

    # Validate the product ID.
    if not product_id or len(product_id) > 100:
        return jsonify(
            success=False,
            error="Please select a valid product."
        ), 400

    try:
        db.execute("BEGIN IMMEDIATE")

        # Confirm that the product exists and is active.
        product = db.execute(
            """
            SELECT id
            FROM products
            WHERE id = ?
              AND is_active = 1
            """,
            (product_id,)
        ).fetchone()

        if not product:
            db.rollback()

            return jsonify(
                success=False,
                error="This product is no longer available."
            ), 404

        if action == "add":

            # INSERT OR IGNORE prevents duplicate wishlist entries.
            db.execute(
                """
                INSERT OR IGNORE INTO wishlist_items
                    (customer_id, product_id)
                VALUES (?, ?)
                """,
                (owner, product_id)
            )

            message = "Product added to wishlist."

        else:

            db.execute(
                """
                DELETE FROM wishlist_items
                WHERE customer_id = ?
                  AND product_id = ?
                """,
                (owner, product_id)
            )

            message = "Product removed from wishlist."

        # Get the updated wishlist count.
        count = db.execute(
            """
            SELECT COUNT(*)
            FROM wishlist_items
            WHERE customer_id = ?
            """,
            (owner,)
        ).fetchone()[0]

        db.commit()

        return jsonify(
            success=True,
            message=message,
            count=count
        )

    except Exception:

        db.rollback()

        return jsonify(
            success=False,
            error="Could not update your wishlist. Please try again."
        ), 500