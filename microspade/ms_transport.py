# microbit-module: ms_transport@0.1.0
"""
Transport layer for microspade.

:class:`RadioTransport` wraps the micro:bit ``radio`` module to send and
receive messages over the built-in 2.4 GHz radio.

For unit testing on a desktop Python environment supply a custom transport
object that implements the same interface (``setup``, ``send``, ``receive``,
``teardown``).
"""


class RadioTransport:
    """
    Transport that uses the micro:bit ``radio`` module.

    Parameters
    ----------
    channel:
        Radio channel (0–83, default 7).  All communicating boards must
        share the same channel.
    power:
        Transmission power level (0–7, default 6).
    queue:
        Maximum number of messages in the receive queue (default 3).
        Increase if messages arrive in bursts.
    length:
        Maximum message length in bytes (default 32, max 251 on V2).
    """

    def __init__(self, channel=7, power=6, queue=3, length=32):
        self.config = {
            "channel": channel,
            "power": power,
            "queue": queue,
            "length": length,
        }
        self._radio = None

    def setup(self):
        """Initialise and enable the radio module."""
        import radio  # noqa: PLC0415  (MicroPython built-in)

        radio.config(**self.config)
        radio.on()
        self._radio = radio

    def send(self, data):
        """Transmit *data* (a string) over the radio."""
        if self._radio:
            self._radio.send(data)

    def receive(self):
        """
        Return the next received string, or ``None`` if the queue is empty.
        """
        return self._radio.receive() if self._radio else None

    def teardown(self):
        """Turn off the radio and release resources."""
        if self._radio:
            self._radio.off()
            self._radio = None

