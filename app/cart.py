"""Browser-specific persistent carts, validated quantities, and two-stack history."""
import json
import secrets
from datetime import timedelta
from flask import Blueprint, current_app, jsonify, render_template, request, session
from .bounded_stack import BoundedStack
from .database import get_db

cart = Blueprint('cart', __name__)
MAX_DISTINCT = 100
MAX_QUANTITY = 999
SCHEMA = '''CREATE TABLE IF NOT EXISTS shopping_carts (
    customer_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 0,
    items_json TEXT NOT NULL DEFAULT '{}',
    undo_json TEXT NOT NULL DEFAULT '[]',
    redo_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)'''


class CartError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def init_cart(app):
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    with app.app_context():
        db = get_db()
        db.execute(SCHEMA)
        db.commit()
    app.register_blueprint(cart)


def customer_id():
    if 'cart_id' not in session:
        session['cart_id'] = secrets.token_hex(24)
    session.permanent = True
    return session['cart_id']


def load(db, owner):
    row = db.execute('SELECT * FROM shopping_carts WHERE customer_id=?', (owner,)).fetchone()
    if row is None:
        return {}, BoundedStack(), BoundedStack(), 0
    return (json.loads(row['items_json']), BoundedStack(json.loads(row['undo_json'])),
            BoundedStack(json.loads(row['redo_json'])), row['version'])


def records(db, ids):
    if not ids:
        return {}
    placeholders = ','.join('?' for _ in ids)
    rows = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', tuple(ids))
    return {row['id']: dict(row) for row in rows}


def snapshot(db, owner):
    items, undo, redo, version = load(db, owner)
    products = records(db, items)
    lines, total = [], 0
    for pid, quantity in items.items():
        product = products.get(pid)
        is_active = bool(product.get('is_active', 1)) if product else False
        unavailable = (product is None) or not is_active
        stock = product['stock'] if (product and is_active) else 0
        price = product['price_paise'] if product else 0
        line_total = price * quantity
        total += line_total
        lines.append(dict(id=pid,
                          name=(product['name'] + ' (Unavailable)') if (product and not is_active) else (product['name'] if product else 'Product no longer available'),
                          image_path=product['image_path'] if product else '', quantity=quantity,
                          price_paise=price, line_total_paise=line_total, stock=stock,
                          unavailable=unavailable, exceeds_stock=quantity > stock))
    return dict(items=lines, count=sum(items.values()), distinct_count=len(items),
                subtotal_paise=total, version=version, can_undo=bool(len(undo)), can_redo=bool(len(redo)),
                undo_label=undo.peek()['label'] if len(undo) else '',
                redo_label=redo.peek()['label'] if len(redo) else '',
                history=[entry['label'] for entry in reversed(undo.items())],
                csrf_token=current_app.jinja_env.globals['csrf_token']())


def integer(value, label, maximum=MAX_QUANTITY):
    if not value.isascii() or not value.isdigit() or len(value) > 10 or int(value) > maximum:
        raise CartError(f'{label} must be a whole number from 0 to {maximum:,}.')
    return int(value)


def apply_changes(db, items, changes, side):
    desired = dict(items)
    for pid, change in changes.items():
        quantity = change[side]
        if quantity:
            desired[pid] = quantity
        else:
            desired.pop(pid, None)
    if len(desired) > MAX_DISTINCT:
        raise CartError(f'A cart can contain at most {MAX_DISTINCT} different products.')
    # Validate changed quantities using live inventory, never values sent by the browser.
    products = records(db, changes)
    for pid, change in changes.items():
        quantity = change[side]
        if quantity:
            if quantity > MAX_QUANTITY:
                raise CartError(f'A cart item can contain at most {MAX_QUANTITY} units.')
            product = products.get(pid)
            if not product or not product.get('is_active', 1):
                raise CartError('This product is no longer available. Remove it from your cart.', 404)
            if quantity > product['stock']:
                raise CartError(f"Only {product['stock']} units of {product['name']} are available.", 409)
    return desired


@cart.get('/cart')
def cart_page():
    customer_id()
    return render_template('cart.html')


@cart.get('/api/cart')
def cart_state():
    db = get_db()
    owner = customer_id()
    db.execute('BEGIN')
    try:
        data = snapshot(db, owner)
        db.commit()
    except Exception:
        db.rollback()
        raise
    response = jsonify(data)
    response.headers['Cache-Control'] = 'no-store'
    return response


@cart.post('/api/cart/action')
def cart_action():
    owner = customer_id()
    db = get_db()
    try:
        db.execute('BEGIN IMMEDIATE')
        items, undo, redo, version = load(db, owner)
        expected = integer(request.form.get('version', ''), 'Cart version', 2_000_000_000)
        if expected != version:
            raise CartError('Your cart changed in another tab. It has been refreshed; try your action again.', 409)
        action = request.form.get('action', '')
        label = ''
        if action in {'undo', 'redo'}:
            source, destination = (undo, redo) if action == 'undo' else (redo, undo)
            if not len(source):
                raise CartError(f'Nothing to {action}.')
            entry = source.peek()
            items = apply_changes(db, items, entry['changes'], 'before' if action == 'undo' else 'after')
            destination.push(source.pop())
            label = f"{'Undid' if action == 'undo' else 'Redid'}: {entry['label']}"
        else:
            if action == 'clear':
                changes = {pid: dict(before=q, after=0) for pid, q in items.items()}
                label = 'Cleared the cart'
            elif action in {'add', 'increment', 'decrement', 'set', 'remove'}:
                pid = request.form.get('product_id', '')
                if not pid or len(pid) > 100:
                    raise CartError('Choose a valid product.')
                before = items.get(pid, 0)
                if action in {'add', 'increment'}:
                    after = before + 1
                elif action == 'decrement':
                    if not before:
                        raise CartError('This item is no longer in your cart.')
                    after = before - 1
                elif action == 'remove':
                    after = 0
                else:
                    after = integer(request.form.get('quantity', ''), 'Quantity')
                product = records(db, [pid]).get(pid)
                name = product['name'] if product else pid
                changes = {pid: dict(before=before, after=after)} if before != after else {}
                label = f'{name}: {before} → {after}'
            else:
                raise CartError('Unknown cart action.')
            if not changes:
                data = snapshot(db, owner)
                db.commit()
                return jsonify(**data, message='No change needed.')
            items = apply_changes(db, items, changes, 'after')
            undo.push(dict(changes=changes, label=label))
            redo = BoundedStack()  # A new edit discards the old redo branch.
        db.execute('''INSERT INTO shopping_carts(customer_id,version,items_json,undo_json,redo_json)
            VALUES (?,?,?,?,?) ON CONFLICT(customer_id) DO UPDATE SET
            version=excluded.version, items_json=excluded.items_json,
            undo_json=excluded.undo_json, redo_json=excluded.redo_json, updated_at=CURRENT_TIMESTAMP''',
            (owner, version + 1, json.dumps(items), json.dumps(undo.items()), json.dumps(redo.items())))
        data = snapshot(db, owner)
        db.commit()
        return jsonify(**data, message=label)
    except CartError as error:
        db.rollback()
        return jsonify(**snapshot(db, owner), error=str(error)), error.status
    except Exception:
        db.rollback()
        current_app.logger.exception('Cart operation failed')
        return jsonify(error='Could not save your cart. Please refresh before retrying.'), 500
