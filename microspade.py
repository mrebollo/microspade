"""
microspade — SPADE-like agents for micro:bit.
Bundled single-file module.
"""

# --- Section: _compat.py ---
try:
    from utime import ticks_ms, ticks_diff, sleep_ms  # MicroPython
except ImportError:
    import time as _time

    def ticks_ms():
        """Return current time in milliseconds (relative, may wrap)."""
        return int(_time.time() * 1000)

    def ticks_diff(new, old):
        """Return signed difference between two ticks values."""
        return new - old

    def sleep_ms(ms):
        """Sleep for *ms* milliseconds."""
        _time.sleep(ms / 1000.0)

# --- Section: mailbox.py ---
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

# --- Section: message.py ---
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

# --- Section: transport.py ---
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

# --- Section: container.py ---
class _AgentContainer:
    """Singleton container that holds all locally-running agents."""

    _instance = None

    def __init__(self):
        self._agents = {}

    @classmethod
    def instance(cls):
        """Return the single shared container."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, agent):
        """Register *agent* so it can receive messages locally."""
        self._agents[agent.name] = agent

    def unregister(self, agent):
        """Remove *agent* from the registry."""
        self._agents.pop(agent.name, None)

    def has_agent(self, name):
        """Return ``True`` when *name* is registered."""
        return name in self._agents

    def get_agent(self, name):
        """Return the agent registered under *name*, or ``None``."""
        return self._agents.get(name)

    def dispatch(self, msg):
        """
        Route *msg* to the local agent named ``msg.to``.

        Returns ``True`` if the message was delivered locally,
        ``False`` if the destination is unknown (caller should use the
        radio transport instead).
        """
        if msg.to is None:
            return False
        agent = self._agents.get(msg.to)
        if agent is not None:
            agent._dispatch(msg)
            return True
        return False

    def reset(self):
        """Remove all registered agents (mainly useful in tests)."""
        self._agents = {}


# Module-level convenience alias
container = _AgentContainer.instance()

# --- Section: behaviour.py ---


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
        self.run()


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
        state.run()

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
            self._current_state = next_name
        elif state._is_done:
            # State killed itself → FSM terminates.
            state.on_end()
            self._is_done = True
        # else: state keeps running (neither transition nor kill).

    def done(self):
        return self._is_done

# --- Section: agent.py ---


class Agent:
    """
    Base class for microspade agents.

    Parameters
    ----------
    name:
        Unique string identifier for this agent.  Used for message
        addressing (equivalent to a SPADE JID).
    transport:
        An object with ``setup()``, ``send(data)``, ``receive()``, and
        ``teardown()`` methods.  Defaults to
        :class:`~microspade.transport.RadioTransport`.
    """

    def __init__(self, name, transport=None):
        self.name = name
        self._transport = transport if transport is not None else RadioTransport()
        self._behaviours = []  # list of dicts: {behaviour, started, template}
        self._running = False

    # ------------------------------------------------------------------
    # User-overridable hooks
    # ------------------------------------------------------------------

    def setup(self):
        """
        Called once when the agent starts.

        Override to add initial behaviours::

            def setup(self):
                self.add_behaviour(MyBehaviour())
        """

    # ------------------------------------------------------------------
    # Behaviour management
    # ------------------------------------------------------------------

    def add_behaviour(self, behaviour, template=None):
        """
        Register *behaviour* with this agent.

        Parameters
        ----------
        behaviour:
            A :class:`~microspade.behaviour.Behaviour` instance.
        template:
            Optional :class:`~microspade.message.MessageTemplate`.
            Only messages that match the template are delivered to this
            behaviour's mailbox.  ``None`` means *receive all*.
        """
        behaviour.set_agent(self)
        self._behaviours.append(
            {"behaviour": behaviour, "started": False, "template": template}
        )

    def remove_behaviour(self, behaviour):
        """Remove *behaviour* from the scheduler."""
        self._behaviours = [
            e for e in self._behaviours if e["behaviour"] is not behaviour
        ]

    def has_behaviour(self, behaviour):
        """Return ``True`` if *behaviour* is currently registered."""
        return any(e["behaviour"] is behaviour for e in self._behaviours)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send(self, message):
        """
        Send *message*.

        The sender field is auto-filled with this agent's name when not
        already set.  The message is delivered locally if the destination
        agent runs in the same program; otherwise it is transmitted over
        the radio transport.
        """
        if message.sender is None:
            message.sender = self.name

        # Try local delivery first (same micro:bit / test environment).
        if message.to is not None and _container.has_agent(message.to):
            _container.dispatch(message)
        else:
            self._transport.send(message.encode())

    def _poll_transport(self):
        """Read one frame from the transport and dispatch it if addressed to us."""
        raw = self._transport.receive()
        if raw:
            msg = Message.decode(raw)
            if msg is not None and self._accepts(msg):
                self._dispatch(msg)

    def _accepts(self, msg):
        """Return ``True`` if this agent should process *msg*."""
        return msg.to is None or msg.to == self.name or msg.to == "*"

    def _dispatch(self, msg):
        """
        Deliver *msg* to the first behaviour whose template matches.

        Unmatched messages are silently discarded (same as SPADE).
        """
        for entry in self._behaviours:
            tmpl = entry["template"]
            if tmpl is None or tmpl.match(msg):
                entry["behaviour"]._mailbox.put(msg)
                return  # deliver to first match only

    # ------------------------------------------------------------------
    # Agent knowledge base (key/value store shared between behaviours)
    # ------------------------------------------------------------------

    def set(self, key, value):
        """Store *value* under *key* in the agent's knowledge base."""
        if not hasattr(self, "_kb"):
            self._kb = {}
        self._kb[key] = value

    def get(self, key):
        """Retrieve a value from the knowledge base, or ``None``."""
        if not hasattr(self, "_kb"):
            return None
        return self._kb.get(key)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Initialise the transport, register in the container and call :meth:`setup`."""
        self._transport.setup()
        _container.register(self)
        self._running = True
        self.setup()

    def stop(self):
        """Stop the scheduler and release the transport."""
        self._running = False
        _container.unregister(self)
        self._transport.teardown()

    def is_alive(self):
        """Return ``True`` while the agent is running."""
        return self._running

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def step(self):
        """
        Perform one full scheduling cycle.

        1. Poll the radio for incoming messages.
        2. Call ``on_start`` on any newly added behaviour.
        3. Call ``_step()`` on each active behaviour.
        4. Remove behaviours that have finished.
        """
        # 1. Receive at most one frame per cycle to stay responsive.
        self._poll_transport()

        # 2 + 3. Step each behaviour.
        to_remove = []
        for entry in self._behaviours:
            b = entry["behaviour"]

            if not entry["started"]:
                b.on_start()
                b._started = True
                entry["started"] = True

            b._step()

            if b.done():
                b.on_end()
                to_remove.append(entry)

        # 4. Remove finished behaviours.
        for entry in to_remove:
            self._behaviours.remove(entry)

    def run(self):
        """
        Start the agent and execute the main scheduling loop.

        Blocks until :meth:`stop` is called or a ``KeyboardInterrupt``
        is received (useful for desktop testing).
        """
        self.start()
        try:
            while self._running:
                self.step()
                sleep_ms(10)
        except KeyboardInterrupt:
            pass
        finally:
            if self._running:
                self.stop()

# --- Exports ---
__version__ = "0.1.0"

__all__ = [
    "Agent",
    "Behaviour",
    "CyclicBehaviour",
    "OneShotBehaviour",
    "PeriodicBehaviour",
    "TimeoutBehaviour",
    "FSMBehaviour",
    "State",
    "Message",
    "MessageTemplate",
    "Mailbox",
    "RadioTransport",
    "container",
]
