# microbit-module: ms_behaviour@0.1.0
"""
Behaviour classes for microspade.

Behaviours are the unit of execution for microspade agents, mirroring the
SPADE behaviour model but implemented with a synchronous cooperative
scheduler suitable for MicroPython on micro:bit.

Class hierarchy
---------------
::

    Behaviour
    ├── CyclicBehaviour      – runs on every scheduler tick until killed
    ├── OneShotBehaviour     – runs exactly once then stops
    ├── PeriodicBehaviour    – runs every *period* seconds
    ├── TimeoutBehaviour     – runs once after *timeout* seconds
    └── FSMBehaviour         – finite-state machine of States
        └── State            – one state inside an FSMBehaviour
"""

from utime import ticks_ms, ticks_diff, sleep_ms
from ms_mailbox import Mailbox


class ReceiveRequest:
    def __init__(self, timeout):
        self.timeout = timeout


class Behaviour:
    """
    Abstract base class for all behaviours.

    Override :meth:`run` with your logic. Override :meth:`on_start` and
    :meth:`on_end` for setup/teardown.
    """

    def __init__(self):
        self.agent = None
        self._is_done = False
        self._started = False
        self._template = None
        self._mailbox = Mailbox()
        self._generator = None
        self._yield_deadline = None
        self._receive_request = None
        self._receive_deadline = None

    # ------------------------------------------------------------------
    # Lifecycle hooks (override in subclasses)
    # ------------------------------------------------------------------

    def on_start(self):
        """Called once before the first :meth:`run` invocation."""

    def run(self):
        """Main behaviour logic. **Must** be overridden."""

    def on_end(self):
        """Called once after the behaviour terminates."""

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def done(self):
        """Return ``True`` when this behaviour should be removed."""
        return self._is_done

    def kill(self):
        """Signal that this behaviour is finished."""
        self._is_done = True

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def receive(self, timeout=0):
        """
        Return the next message from this behaviour's mailbox.

        Parameters
        ----------
        timeout:
            If > 0, returns a :class:`ReceiveRequest` to wait cooperatively
            for a message up to *timeout* seconds using ``yield``.
            Otherwise, returns the next message or ``None`` immediately.

        Returns
        -------
        :class:`~ms_message.Message`, ``None``, or :class:`ReceiveRequest`
        """
        msg = self._mailbox.get()
        if msg:
            return msg
        if timeout > 0:
            return ReceiveRequest(timeout)
        return None

    def send(self, message):
        """Send *message* through the owning agent."""
        if self.agent:
            self.agent.send(message)

    # ------------------------------------------------------------------
    # Agent linkage (called by Agent.add_behaviour)
    # ------------------------------------------------------------------

    def set_agent(self, agent):
        """Link this behaviour to *agent*."""
        self.agent = agent


    # ------------------------------------------------------------------
    # Scheduler interface (called by Agent.step – not public API)
    # ------------------------------------------------------------------

    def _step(self):
        """Execute one scheduler tick."""
        if self._generator is None:
            result = self.run()
            # If the result of calling run() is a generator
            if hasattr(result, "__next__") or hasattr(result, "send"):
                self._generator = result
            else:
                return  # Synchronous run() finished

        # Check if we are currently waiting for a message
        if self._receive_request is not None:
            msg = self._mailbox.get()
            timeout = ticks_diff(self._receive_deadline, ticks_ms()) <= 0
            if msg or timeout:
                self._receive_request = None
                self._receive_deadline = None
                self._resume(msg)
            return

        # Check if we are currently suspended/sleeping
        if self._yield_deadline is not None:
            if ticks_diff(self._yield_deadline, ticks_ms()) > 0:
                return  # Sleep duration hasn't expired yet
            self._yield_deadline = None

        self._resume(None)

    def _resume(self, value=None):
        try:
            val = self._generator.send(value)
            self._handle_yield_value(val)
        except StopIteration:
            self._generator = None
            self._is_done = True

    def _handle_yield_value(self, val):
        # If the yielded value is a number, treat it as a sleep duration in seconds
        if isinstance(val, (int, float)) and val > 0:
            self._yield_deadline = ticks_ms() + int(val * 1000)
        elif isinstance(val, ReceiveRequest):
            self._receive_request = val
            self._receive_deadline = ticks_ms() + int(val.timeout * 1000)

