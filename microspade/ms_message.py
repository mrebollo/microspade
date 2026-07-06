# microbit-module: ms_message@0.1.0
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

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def encode(self):
        """Return the wire-format string for this message."""
        body = str(self.body or "").replace(self._SEP, self._ESC)
        return self._SEP.join([self.to or "", self.sender or "", self.performative or "inform", body])

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
        return cls(
            to=parts[0] or None,
            sender=parts[1] or None,
            performative=parts[2] or "inform",
            body=parts[3].replace(cls._ESC, cls._SEP),
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

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------



    def __repr__(self):
        """NOTE: Only available in debug mode (stripped in production)"""
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
    """

    def __init__(self, to=None, sender=None, performative=None, body=None, check=None):
        self.to = to
        self.sender = sender
        self.performative = performative
        self.body = body
        self.check = check

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
        if self.check is not None and not self.check(message):
            return False
        return True

    def __repr__(self):
        """NOTE: Only available in debug mode (stripped in production)"""
        parts = []
        if self.to is not None:
            parts.append("to={}".format(repr(self.to)))
        if self.sender is not None:
            parts.append("sender={}".format(repr(self.sender)))
        if self.performative is not None:
            parts.append("performative={}".format(repr(self.performative)))
        if self.body is not None:
            parts.append("body={}".format(repr(self.body)))
        if self.check is not None:
            parts.append("check={}".format(repr(self.check)))
        return "MessageTemplate({})".format(", ".join(parts))
