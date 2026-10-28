"""Feature blueprints registration.

Follows the MarketLane project completion plan architecture:
app/features/<feature_name>/
  __init__.py Blueprint export
  routes.py URLs and request validation
  services.py Business logic

Each feature exports a Flask Blueprint from its __init__.py.
`register_features(app)` is invoked once inside `create_app()` before returning `app`.
"""
import importlib
import logging
from pathlib import Path
from flask import Blueprint

logger = logging.getLogger(__name__)


def register_features(app):
    """Register all feature blueprints located in app/features/."""
    features_dir = Path(__file__).resolve().parent

    # 1. Explicit registration of core features
    try:
        from .inventory import inventory_bp
        if inventory_bp.name not in app.blueprints:
            app.register_blueprint(inventory_bp)
    except Exception as e:
        logger.warning(f"Could not load inventory feature blueprint: {e}")

    # 2. Dynamic discovery for additional team features (e.g., orders, activity, pages)
    for folder in features_dir.iterdir():
        if folder.is_dir() and not folder.name.startswith(("_", ".")):
            init_file = folder / "__init__.py"
            if init_file.exists():
                try:
                    mod = importlib.import_module(f".{folder.name}", package=__name__)
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if isinstance(attr, Blueprint) and attr.name not in app.blueprints:
                            app.register_blueprint(attr)
                except Exception as e:
                    logger.debug(f"Feature '{folder.name}' skipped or already loaded: {e}")
