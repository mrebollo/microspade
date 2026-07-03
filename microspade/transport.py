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

    DEFAULT_CHANNEL = 7
    DEFAULT_POWER = 6
    DEFAULT_QUEUE = 3
    DEFAULT_LENGTH = 32

    def __init__(self, channel=None, power=None, queue=None, length=None):
        self._channel = channel if channel is not None else self.DEFAULT_CHANNEL
        self._power = power if power is not None else self.DEFAULT_POWER
        self._queue = queue if queue is not None else self.DEFAULT_QUEUE
        self._length = length if length is not None else self.DEFAULT_LENGTH
        self._radio = None

    def setup(self):
        """Initialise and enable the radio module."""
        import radio  # noqa: PLC0415  (MicroPython built-in)

        radio.config(
            channel=self._channel,
            power=self._power,
            queue=self._queue,
            length=self._length,
        )
        radio.on()
        self._radio = radio

    def send(self, data):
        """Transmit *data* (a string) over the radio."""
        if self._radio is not None:
            self._radio.send(data)

    def receive(self):
        """
        Return the next received string, or ``None`` if the queue is empty.
        """
        if self._radio is not None:
            return self._radio.receive()
        return None

    def teardown(self):
        """Turn off the radio and release resources."""
        if self._radio is not None:
            self._radio.off()
            self._radio = None
