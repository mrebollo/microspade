"""
A simple FIFO message queue (mailbox) for microspade behaviours.

Intentionally kept small to suit the constrained memory of micro:bit.
"""


class Mailbox:
    """
    FIFO queue for :class:`~microspade.message.Message` objects.

    Parameters
    ----------
    capacity:
        Maximum number of messages to hold before new ones are dropped.
        Defaults to 10.
    """

    DEFAULT_CAPACITY = 10

    def __init__(self, capacity=None):
        self._queue = []
        self._capacity = capacity if capacity is not None else self.DEFAULT_CAPACITY

    def put(self, message):
        """
        Enqueue *message*.

        Returns ``True`` on success or ``False`` when the mailbox is full.
        """
        if len(self._queue) >= self._capacity:
            return False
        self._queue.append(message)
        return True

    def get(self):
        """
        Dequeue and return the oldest message, or ``None`` if empty.
        """
        if self._queue:
            return self._queue.pop(0)
        return None

    def empty(self):
        """Return ``True`` when there are no queued messages."""
        return len(self._queue) == 0

    def size(self):
        """Return the number of queued messages."""
        return len(self._queue)

    def clear(self):
        """Discard all queued messages."""
        self._queue = []
