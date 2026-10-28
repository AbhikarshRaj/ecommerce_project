"""Checkout validation and order creation services."""

import json
import re
import secrets
from flask import current_app

from . import order_queue
from ...cart import load, records
from ...database import clean_name


class CheckoutError(Exception):
    """An expected checkout validation or order error."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def checkout_data(db, owner):
    """Build the checkout summary using current database values."""

    items, _undo, _redo, version = load(db, owner)

    if not items:
        raise CheckoutError("Your cart is empty. Add products before checkout.")

    products = records(db, items)
    lines = []
    price_snapshot = {}

    for product_id, quantity in items.items():
        product = products.get(product_id)

        if not product or not product.get("is_active", 1):
            raise CheckoutError(
                "A product in your cart is no longer available. Please review your cart.",
                409
            )

        if quantity > product["stock"]:
            raise CheckoutError(
                f"Only {product['stock']} units of {product['name']} are currently available.",
                409
            )

        price = product["price_paise"]
        line_total = price * quantity
        price_snapshot[product_id] = price

        lines.append({
            "id": product_id,
            "name": product["name"],
            "quantity": quantity,
            "price_paise": price,
            "line_total_paise": line_total,
        })

    cart = {
        "items": lines,
        "version": version,
        "subtotal_paise": sum(
            item["line_total_paise"] for item in lines
        ),
    }

    return {
        "cart": cart,
        "price_snapshot": json.dumps(
            price_snapshot,
            sort_keys=True
        ),
        "submission_token": secrets.token_urlsafe(32),
    }


def _validate_delivery(form):
    """Validate and clean delivery details submitted by the customer."""

    name = clean_name(form.get("customer_name", ""))
    email = form.get("email", "").strip()
    phone = form.get("phone", "").strip()
    address = clean_name(form.get("address", ""))
    city = clean_name(form.get("city", ""))
    state = clean_name(form.get("state", ""))
    postal_code = form.get("postal_code", "").strip()

    if not name or len(name) > 100:
        raise CheckoutError("Enter a valid name (maximum 100 characters).")

    if (
        not email
        or len(email) > 120
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        raise CheckoutError("Enter a valid email address.")

    phone_digits = re.sub(r"[\s+\-()]", "", phone)

    if not phone or not phone_digits.isdigit() or not 7 <= len(phone_digits) <= 15:
        raise CheckoutError("Enter a valid phone number.")

    if not address or len(address) > 500:
        raise CheckoutError("Enter a valid delivery address.")

    if not city or len(city) > 100:
        raise CheckoutError("Enter a valid city.")

    if not state or len(state) > 100:
        raise CheckoutError("Enter a valid state.")

    if not re.fullmatch(r"[A-Za-z0-9 -]{4,10}", postal_code):
        raise CheckoutError("Enter a valid PIN or postal code.")

    if form.get("payment_method") != "COD":
        raise CheckoutError("Only Cash on Delivery is currently available.")

    return {
        "customer_name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "state": state,
        "postal_code": postal_code,
    }


def place_order(db, owner, form):
    """Create an order and deduct stock in one database transaction."""

    details = _validate_delivery(form)
    token = form.get("submission_token", "").strip()

    if not token or len(token) > 100:
        raise CheckoutError("Invalid order submission. Please reload checkout.")

    try:
        submitted_prices = json.loads(form.get("price_snapshot", ""))
        if not isinstance(submitted_prices, dict):
            raise ValueError
    except (ValueError, TypeError):
        raise CheckoutError("Invalid checkout information. Please reload checkout.")

    try:
        expected_version = int(form.get("cart_version", ""))
        if expected_version < 0:
            raise ValueError
    except (ValueError, TypeError):
        raise CheckoutError("Invalid cart version. Please reload checkout.")

    db.execute("BEGIN IMMEDIATE")

    try:
        # A repeated submission with the same token must not create another order.
        existing = db.execute(
            "SELECT id, customer_id FROM orders WHERE submission_token=?",
            (token,)
        ).fetchone()

        if existing:
            if existing["customer_id"] != owner:
                raise CheckoutError("This order submission is not valid.", 409)

            db.commit()
            return existing["id"]

        items, _undo, _redo, version = load(db, owner)

        if not items:
            raise CheckoutError("Your cart is empty.", 409)

        if version != expected_version:
            raise CheckoutError(
                "Your cart has changed. Please review it and try again.",
                409
            )

        products = records(db, items)

        total_paise = 0
        order_lines = []
        current_prices = {}

        for product_id, quantity in items.items():
            product = products.get(product_id)

            if not product or not product.get("is_active", 1):
                raise CheckoutError(
                    "A product in your cart is no longer available.",
                    409
                )

            if quantity > product["stock"]:
                raise CheckoutError(
                    f"Only {product['stock']} units of {product['name']} are available.",
                    409
                )

            price = product["price_paise"]
            current_prices[product_id] = price
            total_paise += price * quantity

            order_lines.append({
                "product_id": product_id,
                "product_name": product["name"],
                "unit_price_paise": price,
                "quantity": quantity,
                "line_total_paise": price * quantity,
            })

        # Never trust prices or totals sent by the browser.
        if submitted_prices != current_prices:
            raise CheckoutError(
                "Product prices have changed. Please review the updated total and place your order again.",
                409
            )

        cursor = db.execute(
            """
            INSERT INTO orders (
                customer_id, customer_name, email, phone,
                address, city, state, postal_code,
                total_paise, payment_method, status,
                cart_version, submission_token
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COD',
                    'Pending', ?, ?)
            """,
            (
                owner,
                details["customer_name"],
                details["email"],
                details["phone"],
                details["address"],
                details["city"],
                details["state"],
                details["postal_code"],
                total_paise,
                version,
                token,
            )
        )

        order_id = cursor.lastrowid

        for item in order_lines:
            stock_update = db.execute(
                """
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
                  AND stock >= ?
                  AND is_active = 1
                """,
                (
                    item["quantity"],
                    item["product_id"],
                    item["quantity"],
                )
            )

            if stock_update.rowcount != 1:
                raise CheckoutError(
                    f"Stock changed for {item['product_name']}. Please review your cart.",
                    409
                )

            db.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_name,
                    unit_price_paise, quantity, line_total_paise
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["unit_price_paise"],
                    item["quantity"],
                    item["line_total_paise"],
                )
            )

        # Clear the cart and its undo/redo history in the same transaction.
        db.execute(
            """
            UPDATE shopping_carts
            SET version = version + 1,
                items_json = '{}',
                undo_json = '[]',
                redo_json = '[]',
                updated_at = CURRENT_TIMESTAMP
            WHERE customer_id = ?
            """,
            (owner,)
        )

        db.commit()

        # Add the committed order to the FIFO queue.
        try:
            order_queue.add(order_id)
        except Exception:
            current_app.logger.exception(
                "Could not update order queue. It will be rebuilt from SQLite."
            )
            try:
                order_queue.rebuild(db)
            except Exception:
                current_app.logger.exception("Could not rebuild order queue.")

        return order_id

    except Exception:
        db.rollback()
        raise


def get_customer_order(db, order_id, owner):
    """Return an order only when it belongs to the current customer."""

    order = db.execute(
        """
        SELECT *
        FROM orders
        WHERE id = ? AND customer_id = ?
        """,
        (order_id, owner)
    ).fetchone()

    if not order:
        return None, []

    items = db.execute(
        """
        SELECT *
        FROM order_items
        WHERE order_id = ?
        ORDER BY id
        """,
        (order_id,)
    ).fetchall()

    return dict(order), [dict(item) for item in items]