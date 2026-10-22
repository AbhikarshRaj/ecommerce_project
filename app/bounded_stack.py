"""A fixed-capacity LIFO stack backed by a circular array.

push/pop/peek: O(1). Export/restore: O(h). When full, discard the oldest
(bottom) entry, so the latest operations remain undoable.
"""
class BoundedStack:
    def __init__(self, items=(), capacity=100):
        if capacity < 1:
            raise ValueError('Capacity must be positive')
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.start = 0
        self.size = 0
        for item in items:
            self.push(item)

    def push(self, item):
        if self.size == self.capacity:
            self.buffer[self.start] = item
            self.start = (self.start + 1) % self.capacity
        else:
            self.buffer[(self.start + self.size) % self.capacity] = item
            self.size += 1

    def pop(self):
        if not self.size:
            raise IndexError('Stack is empty')
        index = (self.start + self.size - 1) % self.capacity
        item = self.buffer[index]
        self.buffer[index] = None
        self.size -= 1
        return item

    def peek(self):
        if not self.size:
            raise IndexError('Stack is empty')
        return self.buffer[(self.start + self.size - 1) % self.capacity]

    def items(self):
        return [self.buffer[(self.start + i) % self.capacity] for i in range(self.size)]

    def __len__(self):
        return self.size
