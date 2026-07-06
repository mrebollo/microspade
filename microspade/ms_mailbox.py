# microbit-module: ms_mailbox@0.1.0
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

    def __init__(self, capacity=10):
        self._queue = []
        self._capacity = capacity

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
        return self._queue.pop(0) if self._queue else None
