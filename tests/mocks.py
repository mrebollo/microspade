"""
Mock transport and helpers for microspade tests.
"""


class MockTransport:
    """
    In-memory transport for testing.

    Messages placed in ``_inbox`` are returned one-at-a-time by
    :meth:`receive`.  Messages sent via :meth:`send` accumulate in
    ``_outbox``.
    """

    def __init__(self):
        self._inbox = []
        self._outbox = []
        self._setup_called = False
        self._teardown_called = False

    def setup(self):
        self._setup_called = True

    def send(self, data):
        self._outbox.append(data)

    def receive(self):
        if self._inbox:
            return self._inbox.pop(0)
        return None

    def teardown(self):
        self._teardown_called = True

    def inject(self, data):
        """Enqueue *data* to be returned by the next :meth:`receive` call."""
        self._inbox.append(data)

    def inject_message(self, message):
        """Encode *message* and enqueue it."""
        self._inbox.append(message.encode())
