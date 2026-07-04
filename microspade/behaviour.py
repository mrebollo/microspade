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


# ---------------------------------------------------------------------------
# Concrete behaviour types
# ---------------------------------------------------------------------------

class CyclicBehaviour(Behaviour):
    """
    A behaviour that runs on every scheduler tick indefinitely.

    It terminates only when :meth:`kill` is called.
    """

    def done(self):
        return self._is_done


class OneShotBehaviour(Behaviour):
    """
    A behaviour that runs exactly once and then terminates automatically.
    """

    def _step(self):
        self.run()
        self._is_done = True


class PeriodicBehaviour(Behaviour):
    """
    A behaviour that calls :meth:`run` every *period* seconds.

    The first invocation happens immediately on the first scheduler tick.

    Parameters
    ----------
    period:
        Interval in **seconds** (float or int) between successive
        :meth:`run` calls.
    """

    def __init__(self, period):
        super().__init__()
        self._period_ms = int(period * 1000)
        self._last_run = None

    def _step(self):
        now = ticks_ms()
        if (
            self._last_run is None
            or ticks_diff(now, self._last_run) >= self._period_ms
        ):
            self._last_run = now
            self.run()

    def done(self):
        return self._is_done


class TimeoutBehaviour(OneShotBehaviour):
    """
    A behaviour that runs exactly once after *timeout* seconds have elapsed.

    Parameters
    ----------
    timeout:
        Delay in **seconds** before :meth:`run` is called.
    """

    def __init__(self, timeout):
        super().__init__()
        self._timeout_ms = int(timeout * 1000)
        self._trigger_at = None
        self._triggered = False

    def on_start(self):
        self._trigger_at = ticks_ms() + self._timeout_ms

    def _step(self):
        if self._triggered:
            return
        now = ticks_ms()
        if self._trigger_at is None:
            return
        if ticks_diff(now, self._trigger_at) >= 0:
            self.run()
            self._triggered = True
            self._is_done = True


# ---------------------------------------------------------------------------
# FSM behaviour
# ---------------------------------------------------------------------------

class State(Behaviour):
    """
    A single state inside a :class:`FSMBehaviour`.

    Inside :meth:`run`, call :meth:`set_next_state` to request a
    transition.  Call :meth:`kill` (or do neither) to keep looping in
    the same state / terminate the FSM respectively.
    """

    def __init__(self):
        super().__init__()
        self._next_state = None

    def set_next_state(self, state_name):
        """Request a transition to the state named *state_name*."""
        self._next_state = state_name


class FSMBehaviour(Behaviour):
    """
    A Finite State Machine behaviour.

    States are :class:`State` instances registered with :meth:`add_state`.
    Valid transitions between states can optionally be declared with
    :meth:`add_transition`; if no transitions are registered the FSM
    permits any transition.

    Example
    -------
    ::

        class StateA(State):
            def run(self):
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                self.kill()  # terminal – ends the FSM

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())
        agent.add_behaviour(fsm)
    """

    def __init__(self):
        super().__init__()
        self._states = {}
        self._transitions = {}
        self._current_state = None

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    def add_state(self, name, state, initial=False):
        """
        Register *state* under *name*.

        Parameters
        ----------
        name:
            Unique string identifier for the state.
        state:
            A :class:`State` instance.
        initial:
            If ``True`` this state is the starting state.  The first
            state added is used as the default initial state if no state
            is explicitly marked as initial.
        """
        self._states[name] = state
        if initial or self._current_state is None:
            self._current_state = name

    def add_transition(self, source, dest):
        """
        Declare a valid transition from *source* to *dest*.

        When at least one transition is declared the FSM validates every
        :meth:`~State.set_next_state` call.  If no transitions are
        declared all transitions are permitted.
        """
        if source not in self._transitions:
            self._transitions[source] = []
        if dest not in self._transitions[source]:
            self._transitions[source].append(dest)

    def is_valid_transition(self, source, dest):
        """Return ``True`` if the transition from *source* to *dest* is allowed."""
        if not self._transitions:
            return True
        return dest in self._transitions.get(source, [])

    def set_agent(self, agent):
        self._agent = agent
        self._mailbox = Mailbox()
        for state in self._states.values():
            state.set_agent(agent)
            # States share the FSM's mailbox so receive() works naturally.
            state._mailbox = self._mailbox

    @property
    def current_state(self):
        """The name of the currently active state."""
        return self._current_state

    # ------------------------------------------------------------------
    # Scheduler interface
    # ------------------------------------------------------------------

    def _step(self):
        if self._is_done:
            return

        if self._current_state is None:
            self._is_done = True
            return

        state = self._states.get(self._current_state)
        if state is None:
            self._is_done = True
            return

        # Call on_start exactly once per state entry.
        if not state._started:
            state.on_start()
            state._started = True

        state._next_state = None
        state._step()

        next_name = state._next_state
        if next_name is not None:
            # Transition requested.
            if self._transitions and not self.is_valid_transition(
                self._current_state, next_name
            ):
                # Invalid transition: stay in current state.
                return
            state.on_end()
            state._started = False
            state._is_done = False
            state._reset_generator()
            self._current_state = next_name
        elif state._is_done:
            # State killed itself → FSM terminates.
            state.on_end()
            state._reset_generator()
            self._is_done = True
        # else: state keeps running (neither transition nor kill).

    def done(self):
        return self._is_done
