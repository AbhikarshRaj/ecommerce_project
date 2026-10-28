"""Checkout and customer order routes."""

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
)

from functools import wraps

from . import orders, order_queue
from ...admin import login_required
from .services import (
    CheckoutError,
    checkout_data,
    place_order as create_order,
    get_customer_order,
)
from ...cart import customer_id
from ...database import get_db


@orders.get("/checkout")
def checkout():
    owner = customer_id()
    db = get_db()

    try:
        data = checkout_data(db, owner)

    except CheckoutError as error:
        flash(str(error), "error")
        return redirect(url_for("cart.cart_page"))

    return render_template(
        "checkout.html",
        **data,
        error=None,
        success=None,
    )


@orders.post("/place")
def place_order():
    owner = customer_id()
    db = get_db()

    try:
        order_id = create_order(db, owner, request.form)

    except CheckoutError as error:
        # Refresh the checkout page with current cart and prices.
        try:
            data = checkout_data(db, owner)
        except CheckoutError:
            flash(str(error), "error")
            return redirect(url_for("cart.cart_page"))

        return render_template(
            "checkout.html",
            **data,
            error=str(error),
            success=None,
        ), error.status

    return redirect(url_for("orders.order_confirmation", order_id=order_id))


@orders.get("/confirmation/<int:order_id>")
def order_confirmation(order_id):
    owner = customer_id()
    db = get_db()

    order, items = get_customer_order(db, order_id, owner)

    if order is None:
        abort(404)

    return render_template(
        "order_confirmation.html",
        order=order,
        items=items,
    )

ORDER_STATUSES = ["Pending", "Processing", "Shipped", "Delivered"]


@orders.get("/admin")
@login_required
def admin_orders():
    db = get_db()

    selected_status = request.args.get("status", "").strip()

    if selected_status and selected_status not in ORDER_STATUSES:
        abort(400)

    if selected_status:
        rows = db.execute(
            """
            SELECT *
            FROM orders
            WHERE status = ?
            ORDER BY created_at DESC, id DESC
            """,
            (selected_status,)
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT *
            FROM orders
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return render_template(
        "admin_orders.html",
        orders_list=[dict(row) for row in rows],
        statuses=ORDER_STATUSES,
        selected_status=selected_status,
    )


@orders.post("/admin/process-next")
@login_required
def process_next():
    db = get_db()

    # Serialize queue operations and database claims.
    with order_queue.lock:
        try:
            db.execute("BEGIN IMMEDIATE")

            # Restore the queue if it is empty.
            if not order_queue.pending:
                order_queue.rebuild(db)

            order_id = None

            # Remove stale queue entries until a Pending order is found.
            while order_queue.pending:
                candidate = order_queue.pending[0]

                row = db.execute(
                    "SELECT status FROM orders WHERE id = ?",
                    (candidate,)
                ).fetchone()

                if row and row["status"] == "Pending":
                    order_id = candidate
                    break

                order_queue.pending.popleft()

            if order_id is None:
                db.commit()
                flash("There are no pending orders to process.", "info")
                return redirect(url_for("orders.admin_orders"))

            updated = db.execute(
                """
                UPDATE orders
                SET status = 'Processing'
                WHERE id = ? AND status = 'Pending'
                """,
                (order_id,)
            )

            if updated.rowcount != 1:
                raise RuntimeError("Could not claim the pending order.")

            db.execute(
                """
                INSERT INTO order_status_events
                    (order_id, old_status, new_status, changed_by)
                VALUES (?, 'Pending', 'Processing', 'admin')
                """,
                (order_id,)
            )

            db.commit()

            # Remove the claimed order only after the commit succeeds.
            order_queue.pending.popleft()

            flash(f"Order #{order_id} is now Processing.", "success")

        except Exception:
            db.rollback()
            order_queue.rebuild(db)
            raise

    return redirect(url_for("orders.admin_orders"))

@orders.get("/admin/<int:order_id>")
@login_required
def admin_order_detail(order_id):
    db = get_db()

    order = db.execute(
        "SELECT * FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()

    if not order:
        abort(404)

    items = db.execute(
        """
        SELECT *
        FROM order_items
        WHERE order_id = ?
        ORDER BY id
        """,
        (order_id,)
    ).fetchall()

    events = db.execute(
        """
        SELECT *
        FROM order_status_events
        WHERE order_id = ?
        ORDER BY changed_at, id
        """,
        (order_id,)
    ).fetchall()

    next_status = {
        "Pending": "Processing",
        "Processing": "Shipped",
        "Shipped": "Delivered",
        "Delivered": None,
    }[order["status"]]

    return render_template(
        "admin_order_detail.html",
        order=dict(order),
        items=[dict(item) for item in items],
        events=[dict(event) for event in events],
        next_status=next_status,
    )


@orders.post("/admin/<int:order_id>/status")
@login_required
def update_order_status(order_id):
    db = get_db()

    transitions = {
        "Pending": "Processing",
        "Processing": "Shipped",
        "Shipped": "Delivered",
    }

    requested_status = request.form.get("new_status", "")

    try:
        db.execute("BEGIN IMMEDIATE")

        order = db.execute(
            "SELECT status FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()

        if not order:
            abort(404)

        current_status = order["status"]
        expected_next = transitions.get(current_status)

        if expected_next != requested_status:
            db.rollback()
            flash("Invalid status transition. Refresh the order page.", "error")
            return redirect(
                url_for("orders.admin_order_detail", order_id=order_id)
            )

        updated = db.execute(
            """
            UPDATE orders
            SET status = ?
            WHERE id = ? AND status = ?
            """,
            (requested_status, order_id, current_status)
        )

        if updated.rowcount != 1:
            raise RuntimeError("Order status could not be updated.")

        db.execute(
            """
            INSERT INTO order_status_events
                (order_id, old_status, new_status, changed_by)
            VALUES (?, ?, ?, 'admin')
            """,
            (order_id, current_status, requested_status)
        )

        db.commit()

        # Keep the in-memory queue synchronized.
        if requested_status != "Pending":
            order_queue.remove(order_id)

        flash(
            f"Order #{order_id} updated to {requested_status}.",
            "success"
        )

    except Exception:
        db.rollback()
        raise

    return redirect(
        url_for("orders.admin_order_detail", order_id=order_id)
    )