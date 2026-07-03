"""
Agent base class for microspade.

An :class:`Agent` owns a list of :class:`~microspade.behaviour.Behaviour`
objects and drives them through a cooperative scheduler.  Communication
uses the micro:bit radio (via :class:`~microspade.transport.RadioTransport`)
for cross-board messaging and an in-process
:class:`~microspade.container.container` for same-board local routing.

Typical usage
-------------
::

    from microspade import Agent, CyclicBehaviour, Message

    class Greeter(CyclicBehaviour):
        def run(self):
            msg = self.receive()
            if msg:
                print("Got:", msg.body)

    class MyAgent(Agent):
        def setup(self):
            self.add_behaviour(Greeter())

    agent = MyAgent("greeter")
    agent.run()       # blocks forever (press Ctrl-C to stop)
"""

from microspade.message import Message
from microspade.transport import RadioTransport
from microspade.container import container as _container
from microspade._compat import sleep_ms


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
