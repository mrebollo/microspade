"""
ping_pong.py — Two micro:bits exchanging ping/pong messages.

Flash this program to **both** boards.  Set ``IS_INITIATOR = True`` on
one board and ``IS_INITIATOR = False`` on the other.  Both boards must
be on the same radio channel (default 7).

The initiating board sends the first "ping".  Each board then replies
with the opposite message.  The current count scrolls across the display.
"""

from microbit import display, sleep  # noqa: F401  (micro:bit builtins)
from microspade import Agent, CyclicBehaviour, Message, MessageTemplate

# ------------------------------------------------------------------
# Configuration — change these per-board
# ------------------------------------------------------------------
AGENT_NAME = "pinger"    # unique name for *this* board
PEER_NAME = "ponger"     # name of the *other* board
IS_INITIATOR = True      # True on one board, False on the other
CHANNEL = 7              # radio channel – must match on both boards


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class PingPongBehaviour(CyclicBehaviour):
    """Exchanges ping/pong messages with a peer agent."""

    def __init__(self, peer, is_initiator):
        super().__init__()
        self._peer = peer
        self._is_initiator = is_initiator
        self._count = 0

    def on_start(self):
        if self._is_initiator:
            self._send_ping()

    def run(self):
        msg = self.receive(timeout=0.1)
        if msg is None:
            return

        self._count += 1
        display.scroll(str(self._count), wait=False)

        # Reply with the opposite message
        reply_body = "pong" if msg.body == "ping" else "ping"
        reply = Message(to=self._peer, body=reply_body, performative="request")
        self.send(reply)

    def _send_ping(self):
        msg = Message(to=self._peer, body="ping", performative="request")
        self.send(msg)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class PingPongAgent(Agent):
    def __init__(self, name, peer, is_initiator, channel):
        from microspade import RadioTransport
        super().__init__(name, transport=RadioTransport(channel=channel))
        self._peer = peer
        self._is_initiator = is_initiator

    def setup(self):
        template = MessageTemplate(performative="request")
        self.add_behaviour(
            PingPongBehaviour(self._peer, self._is_initiator),
            template=template,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

agent = PingPongAgent(AGENT_NAME, PEER_NAME, IS_INITIATOR, CHANNEL)
agent.run()
