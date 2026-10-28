"""FIFO queue for processing pending customer orders."""

from collections import deque
from threading import RLock


class OrderQueue:
    def __init__(self):
        self.pending = deque()
        self.lock = RLock()

    def rebuild(self, db):
        """Rebuild the queue from SQLite in FIFO order."""

        with self.lock:
            rows = db.execute("""
                SELECT id
                FROM orders
                WHERE status = 'Pending'
                ORDER BY created_at ASC, id ASC
            """).fetchall()

            self.pending = deque(row["id"] for row in rows)

    def add(self, order_id):
        """Add a newly created order to the end of the queue."""

        with self.lock:
            if order_id not in self.pending:
                self.pending.append(order_id)

    def remove(self, order_id):
        """Remove an order from the queue if it exists."""

        with self.lock:
            try:
                self.pending.remove(order_id)
            except ValueError:
                pass

    def next_order(self):
        """Return the next order ID without removing it."""

        with self.lock:
            return self.pending[0] if self.pending else None

    def pop(self):
        """Remove and return the oldest order ID."""

        with self.lock:
            return self.pending.popleft() if self.pending else None

    def snapshot(self):
        """Return a safe copy of the current queue."""

        with self.lock:
            return list(self.pending)