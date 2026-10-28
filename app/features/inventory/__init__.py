"""Inventory feature blueprint export.

Follows the MarketLane feature folder convention:
app/features/inventory/
  __init__.py Blueprint export
  routes.py URLs and request validation
  services.py Business logic
"""
from .routes import inventory_bp

__all__ = ["inventory_bp"]
