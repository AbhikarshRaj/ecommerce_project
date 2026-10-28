from flask import Blueprint

from .queue import OrderQueue

orders = Blueprint("orders", __name__, url_prefix="/orders")

order_queue = OrderQueue()

from . import routes