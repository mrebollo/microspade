"""
microspade — SPADE-like agents for micro:bit.
Bundled single-file module.
"""

# --- Section: _compat.py ---
try:
    from utime import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    import time as _time

    def ticks_ms():
        return int(_time.time() * 1000)

    def ticks_diff(new, old):
        return new - old

    def sleep_ms(ms):
        _time.sleep(ms / 1000.0)

# --- Section: mailbox.py ---
class Mailbox:
    DEFAULT_CAPACITY = 10

    def __init__(self, capacity=None):
        self._queue = []
        self._capacity = capacity if capacity is not None else self.DEFAULT_CAPACITY

    def put(self, message):
        if len(self._queue) >= self._capacity:
            return False
        self._queue.append(message)
        return True

    def get(self):
        if self._queue:
            return self._queue.pop(0)
        return None

    def empty(self):
        return len(self._queue) == 0

    def size(self):
        return len(self._queue)

    def clear(self):
        self._queue = []

# --- Section: message.py ---
class Message:
    _SEP = '|'
    _ESC = '\\|'

    def __init__(self, to=None, sender=None, body='', performative='inform'):
        self.to = to
        self.sender = sender
        self.body = body if body is not None else ''
        self.performative = performative if performative is not None else 'inform'
        self.metadata = {}

    def encode(self):
        to = self.to if self.to is not None else ''
        sender = self.sender if self.sender is not None else ''
        perf = self.performative if self.performative is not None else 'inform'
        body = str(self.body) if self.body is not None else ''
        body = body.replace(self._SEP, self._ESC)
        return self._SEP.join([to, sender, perf, body])

    @classmethod
    def decode(cls, raw):
        if not raw:
            return None
        parts = raw.split(cls._SEP, 3)
        if len(parts) < 4:
            return None
        body = parts[3].replace(cls._ESC, cls._SEP)
        return cls(to=parts[0] if parts[0] else None, sender=parts[1] if parts[1] else None, performative=parts[2] if parts[2] else 'inform', body=body)

    def make_reply(self):
        return Message(to=self.sender, sender=self.to, body='', performative=self.performative)

    def set_metadata(self, key, value):
        self.metadata[key] = value

    def get_metadata(self, key):
        return self.metadata.get(key)

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return self.to == other.to and self.sender == other.sender and (self.performative == other.performative) and (self.body == other.body)

    def __repr__(self):
        return 'Message(to={}, sender={}, performative={}, body={})'.format(repr(self.to), repr(self.sender), repr(self.performative), repr(self.body))

class MessageTemplate:

    def __init__(self, to=None, sender=None, performative=None, body=None):
        self.to = to
        self.sender = sender
        self.performative = performative
        self.body = body

    def match(self, message):
        if self.to is not None and message.to != self.to:
            return False
        if self.sender is not None and message.sender != self.sender:
            return False
        if self.performative is not None and message.performative != self.performative:
            return False
        if self.body is not None and message.body != self.body:
            return False
        return True

    def __and__(self, other):
        return _AndTemplate(self, other)

    def __or__(self, other):
        return _OrTemplate(self, other)

    def __invert__(self):
        return _NotTemplate(self)

    def __repr__(self):
        parts = []
        if self.to is not None:
            parts.append('to={}'.format(repr(self.to)))
        if self.sender is not None:
            parts.append('sender={}'.format(repr(self.sender)))
        if self.performative is not None:
            parts.append('performative={}'.format(repr(self.performative)))
        if self.body is not None:
            parts.append('body={}'.format(repr(self.body)))
        return 'MessageTemplate({})'.format(', '.join(parts))

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
        import radio
        radio.config(channel=self._channel, power=self._power, queue=self._queue, length=self._length)
        radio.on()
        self._radio = radio

    def send(self, data):
        if self._radio is not None:
            self._radio.send(data)

    def receive(self):
        if self._radio is not None:
            return self._radio.receive()
        return None

    def teardown(self):
        if self._radio is not None:
            self._radio.off()
            self._radio = None

# --- Section: container.py ---
class _AgentContainer:
    _instance = None

    def __init__(self):
        self._agents = {}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, agent):
        self._agents[agent.name] = agent

    def unregister(self, agent):
        self._agents.pop(agent.name, None)

    def has_agent(self, name):
        return name in self._agents

    def get_agent(self, name):
        return self._agents.get(name)

    def dispatch(self, msg):
        if msg.to is None:
            return False
        agent = self._agents.get(msg.to)
        if agent is not None:
            agent._dispatch(msg)
            return True
        return False

    def reset(self):
        self._agents = {}
container = _AgentContainer.instance()

# --- Section: behaviour.py ---

class Behaviour:

    def __init__(self):
        self._agent = None
        self._is_done = False
        self._started = False
        self._mailbox = Mailbox()

    def on_start(self):

    def run(self):

    def on_end(self):

    def done(self):
        return self._is_done

    def kill(self, exit_code=0):
        self._is_done = True

    def receive(self, timeout=0):
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
        if self._agent is not None:
            self._agent.send(message)

    def set_agent(self, agent):
        self._agent = agent

    @property
    def agent(self):
        return self._agent

    def _step(self):
        self.run()

class CyclicBehaviour(Behaviour):

    def done(self):
        return self._is_done

class OneShotBehaviour(Behaviour):

    def _step(self):
        self.run()
        self._is_done = True

class PeriodicBehaviour(Behaviour):

    def __init__(self, period):
        super().__init__()
        self._period_ms = int(period * 1000)
        self._last_run = None

    def _step(self):
        now = ticks_ms()
        if self._last_run is None or ticks_diff(now, self._last_run) >= self._period_ms:
            self._last_run = now
            self.run()

    def done(self):
        return self._is_done

class TimeoutBehaviour(OneShotBehaviour):

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

class State(Behaviour):

    def __init__(self):
        super().__init__()
        self._next_state = None

    def set_next_state(self, state_name):
        self._next_state = state_name

class FSMBehaviour(Behaviour):

    def __init__(self):
        super().__init__()
        self._states = {}
        self._transitions = {}
        self._current_state = None

    def add_state(self, name, state, initial=False):
        self._states[name] = state
        if initial or self._current_state is None:
            self._current_state = name

    def add_transition(self, source, dest):
        if source not in self._transitions:
            self._transitions[source] = []
        if dest not in self._transitions[source]:
            self._transitions[source].append(dest)

    def is_valid_transition(self, source, dest):
        if not self._transitions:
            return True
        return dest in self._transitions.get(source, [])

    def set_agent(self, agent):
        self._agent = agent
        self._mailbox = Mailbox()
        for state in self._states.values():
            state.set_agent(agent)
            state._mailbox = self._mailbox

    @property
    def current_state(self):
        return self._current_state

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
        if not state._started:
            state.on_start()
            state._started = True
        state._next_state = None
        state.run()
        next_name = state._next_state
        if next_name is not None:
            if self._transitions and (not self.is_valid_transition(self._current_state, next_name)):
                return
            state.on_end()
            state._started = False
            state._is_done = False
            self._current_state = next_name
        elif state._is_done:
            state.on_end()
            self._is_done = True

    def done(self):
        return self._is_done

# --- Section: agent.py ---

class Agent:

    def __init__(self, name, transport=None):
        self.name = name
        self._transport = transport if transport is not None else RadioTransport()
        self._behaviours = []
        self._running = False

    def setup(self):

    def add_behaviour(self, behaviour, template=None):
        behaviour.set_agent(self)
        self._behaviours.append({'behaviour': behaviour, 'started': False, 'template': template})

    def remove_behaviour(self, behaviour):
        self._behaviours = [e for e in self._behaviours if e['behaviour'] is not behaviour]

    def has_behaviour(self, behaviour):
        return any((e['behaviour'] is behaviour for e in self._behaviours))

    def send(self, message):
        if message.sender is None:
            message.sender = self.name
        if message.to is not None and container.has_agent(message.to):
            container.dispatch(message)
        else:
            self._transport.send(message.encode())

    def _poll_transport(self):
        raw = self._transport.receive()
        if raw:
            msg = Message.decode(raw)
            if msg is not None and self._accepts(msg):
                self._dispatch(msg)

    def _accepts(self, msg):
        return msg.to is None or msg.to == self.name or msg.to == '*'

    def _dispatch(self, msg):
        for entry in self._behaviours:
            tmpl = entry['template']
            if tmpl is None or tmpl.match(msg):
                entry['behaviour']._mailbox.put(msg)
                return

    def set(self, key, value):
        if not hasattr(self, '_kb'):
            self._kb = {}
        self._kb[key] = value

    def get(self, key):
        if not hasattr(self, '_kb'):
            return None
        return self._kb.get(key)

    def start(self):
        self._transport.setup()
        container.register(self)
        self._running = True
        self.setup()

    def stop(self):
        self._running = False
        container.unregister(self)
        self._transport.teardown()

    def is_alive(self):
        return self._running

    def step(self):
        self._poll_transport()
        to_remove = []
        for entry in self._behaviours:
            b = entry['behaviour']
            if not entry['started']:
                b.on_start()
                b._started = True
                entry['started'] = True
            b._step()
            if b.done():
                b.on_end()
                to_remove.append(entry)
        for entry in to_remove:
            self._behaviours.remove(entry)

    def run(self):
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
