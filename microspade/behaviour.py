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

from microspade._compat import ticks_ms, ticks_diff, sleep_ms
from microspade.mailbox import Mailbox


class Behaviour:
    """
    Abstract base class for all behaviours.

    Override :meth:`run` with your logic. Override :meth:`on_start` and
    :meth:`on_end` for setup/teardown.
    """

    def __init__(self):
        self._agent = None
        self._is_done = False
        self._started = False
        self._mailbox = Mailbox()
        self._generator = None
        self._yield_deadline = None

    def _reset_generator(self):
        self._generator = None
        self._yield_deadline = None

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

    def kill(self, exit_code=0):
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
            If > 0, wait up to *timeout* **seconds** before returning
            ``None``.  During the wait the agent's transport is polled
            so incoming radio messages can arrive.

        Returns
        -------
        :class:`~microspade.message.Message` or ``None``
        """
        msg = self._mailbox.get()
        if msg is not None:
            return msg
        if timeout > 0:
            deadline = ticks_ms() + int(timeout * 1000)
            while True:
                if self._agent is not None:
                    self._agent._poll_transport()
                msg = self._mailbox.get()
                if msg is not None:
                    return msg
                remaining = ticks_diff(deadline, ticks_ms())
                if remaining <= 0:
                    break
                sleep_ms(min(10, remaining))
        return None

    def send(self, message):
        """Send *message* through the owning agent."""
        if self._agent is not None:
            self._agent.send(message)

    # ------------------------------------------------------------------
    # Agent linkage (called by Agent.add_behaviour)
    # ------------------------------------------------------------------

    def set_agent(self, agent):
        """Link this behaviour to *agent*."""
        self._agent = agent

    @property
    def agent(self):
        """The owning :class:`~microspade.agent.Agent`."""
        return self._agent

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

        # Check if we are currently suspended/sleeping
        if self._yield_deadline is not None:
            if ticks_diff(self._yield_deadline, ticks_ms()) > 0:
                return  # Sleep duration hasn't expired yet
            else:
                self._yield_deadline = None

        try:
            val = next(self._generator)
            # If the yielded value is a number, treat it as a sleep duration in seconds
            if isinstance(val, (int, float)) and val > 0:
                self._yield_deadline = ticks_ms() + int(val * 1000)
        except StopIteration:
            self._generator = None
            self._is_done = True

