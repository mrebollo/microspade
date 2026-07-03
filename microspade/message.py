"""
Message and MessageTemplate classes for microspade.

Messages are serialised as a pipe-delimited string so they can be
transmitted over the micro:bit radio (which only transports strings).

Wire format:  ``TO|FROM|PERFORMATIVE|BODY``

Any ``|`` characters inside *body* are escaped to ``\\|`` so that the
four-field structure is always preserved on decode.
"""


class Message:
    """A message exchanged between microspade agents."""

    _SEP = "|"
    _ESC = "\\|"

    def __init__(self, to=None, sender=None, body="", performative="inform"):
        self.to = to
        self.sender = sender
        self.body = body if body is not None else ""
        self.performative = performative if performative is not None else "inform"
        self.metadata = {}

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def encode(self):
        """Return the wire-format string for this message."""
        to = self.to if self.to is not None else ""
        sender = self.sender if self.sender is not None else ""
        perf = self.performative if self.performative is not None else "inform"
        body = str(self.body) if self.body is not None else ""
        # Escape any separator characters inside the body field.
        body = body.replace(self._SEP, self._ESC)
        return self._SEP.join([to, sender, perf, body])

    @classmethod
    def decode(cls, raw):
        """
        Decode a wire-format string into a :class:`Message`.

        Returns ``None`` for empty or malformed strings.
        """
        if not raw:
            return None
        parts = raw.split(cls._SEP, 3)
        if len(parts) < 4:
            return None
        body = parts[3].replace(cls._ESC, cls._SEP)
        return cls(
            to=parts[0] if parts[0] else None,
            sender=parts[1] if parts[1] else None,
            performative=parts[2] if parts[2] else "inform",
            body=body,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def make_reply(self):
        """Return a new :class:`Message` with *to* and *sender* swapped."""
        return Message(
            to=self.sender,
            sender=self.to,
            body="",
            performative=self.performative,
        )

    def set_metadata(self, key, value):
        """Store an arbitrary metadata value (string key/value pair)."""
        self.metadata[key] = value

    def get_metadata(self, key):
        """Return a metadata value, or ``None`` if not present."""
        return self.metadata.get(key)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return (
            self.to == other.to
            and self.sender == other.sender
            and self.performative == other.performative
            and self.body == other.body
        )

    def __repr__(self):
        return "Message(to={}, sender={}, performative={}, body={})".format(
            repr(self.to),
            repr(self.sender),
            repr(self.performative),
            repr(self.body),
        )


class MessageTemplate:
    """
    Filter used to route incoming messages to a specific behaviour.

    Any field set to a non-``None`` value is matched exactly.
    Fields left as ``None`` act as wildcards.

    Boolean operators ``&``, ``|``, and ``~`` can be used to combine
    templates (AND, OR, NOT).
    """

    def __init__(self, to=None, sender=None, performative=None, body=None):
        self.to = to
        self.sender = sender
        self.performative = performative
        self.body = body

    def match(self, message):
        """Return ``True`` if *message* satisfies every constraint."""
        if self.to is not None and message.to != self.to:
            return False
        if self.sender is not None and message.sender != self.sender:
            return False
        if self.performative is not None and message.performative != self.performative:
            return False
        if self.body is not None and message.body != self.body:
            return False
        return True

    # ------------------------------------------------------------------
    # Boolean composition
    # ------------------------------------------------------------------

    def __and__(self, other):
        return _AndTemplate(self, other)

    def __or__(self, other):
        return _OrTemplate(self, other)

    def __invert__(self):
        return _NotTemplate(self)

    def __repr__(self):
        parts = []
        if self.to is not None:
            parts.append("to={}".format(repr(self.to)))
        if self.sender is not None:
            parts.append("sender={}".format(repr(self.sender)))
        if self.performative is not None:
            parts.append("performative={}".format(repr(self.performative)))
        if self.body is not None:
            parts.append("body={}".format(repr(self.body)))
        return "MessageTemplate({})".format(", ".join(parts))


class _AndTemplate:
    def __init__(self, left, right):
        self._left = left
        self._right = right

    def match(self, message):
        return self._left.match(message) and self._right.match(message)


class _OrTemplate:
    def __init__(self, left, right):
        self._left = left
        self._right = right

    def match(self, message):
        return self._left.match(message) or self._right.match(message)


class _NotTemplate:
    def __init__(self, inner):
        self._inner = inner

    def match(self, message):
        return not self._inner.match(message)
