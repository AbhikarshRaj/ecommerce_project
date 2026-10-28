import secrets
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, abort
from .database import get_db, close_db, initialize, clean_name
from .catalog_store import CatalogStore
from .activity import cleanup_old_logs


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "ecommerce.db"),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        UPLOAD_FOLDER=str(Path(app.static_folder) / "uploads" / "products"),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        secret_file = Path(app.instance_path) / "session.key"
        try:
            with secret_file.open("x", encoding="utf-8") as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config["SECRET_KEY"] = secret_file.read_text(encoding="utf-8").strip()
    app.teardown_appcontext(close_db)

    with app.app_context():
        initialize()

        db = get_db()
        with db:
            deleted_count = cleanup_old_logs(db, retention_days=90)

        app.logger.info(
            "Activity log cleanup completed. Deleted %d old records.",
            deleted_count
        )

    app.extensions["catalog_store"] = CatalogStore()

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        return session["csrf"]
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def verify_csrf():
        if request.method == "POST":
            expected = session.get("csrf", "")
            actual = request.form.get("csrf_token", "")
            if not expected or not secrets.compare_digest(expected, actual):
                abort(400, description="Form expired. Reload the page and try again.")

    def taxonomy():
        db = get_db()
        categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY name COLLATE NOCASE")]
        subcategories = [dict(r) for r in db.execute("SELECT * FROM subcategories ORDER BY name COLLATE NOCASE")]
        return categories, subcategories

    @app.route("/")
    def catalog():
        categories, subcategories = taxonomy()
        products = app.extensions["catalog_store"].select()
        return render_template("catalog.html", products=products,
                               categories=categories, subcategories=subcategories)

    @app.get("/api/catalog")
    def catalog_api():
        def selected_id(key):
            value = request.args.get(key, "")
            if not value or value == "all":
                return None
            if not value.isascii() or not value.isdigit() or len(value) > 12:
                abort(400)
            return int(value)
        products = app.extensions["catalog_store"].select(
            selected_id("category"), selected_id("subcategory"), request.args.get("q", "")[:200])
        return jsonify(html=render_template("_product_cards.html", products=products), count=len(products))

    @app.post('/contact')
    def submit_contact():
        name = clean_name(request.form.get('name', ''))
        email = request.form.get('email', '').strip()
        subject = clean_name(request.form.get('subject', ''))
        message = request.form.get('message', '').strip()

        if not name or len(name) > 100:
            return jsonify(success=False, error='Please enter your name (up to 100 characters).'), 400
        if not email or '@' not in email or len(email) > 120:
            return jsonify(success=False, error='Please enter a valid email address.'), 400
        if not message or len(message) < 5 or len(message) > 2000:
            return jsonify(success=False, error='Message must be between 5 and 2000 characters.'), 400

        db = get_db()
        with db:
            db.execute(
                'INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)',
                (name, email, subject[:120], message)
            )
        return jsonify(
            success=True,
            message=f'Thank you, {name}! Your message has been received. Our team will get back to you shortly.'
        )

    @app.errorhandler(413)
    def too_large(_error):
        return "Upload too large. Go back and select an image under 5 MB.", 413

    from .admin import admin, register_commands
    app.register_blueprint(admin)
    register_commands(app)

    from .cart import init_cart
    init_cart(app)

    from .features.orders import orders, order_queue
    app.register_blueprint(orders)

    # Restore pending orders into the FIFO queue at application startup.
    with app.app_context():
        order_queue.rebuild(get_db())

    return app
