"""
simple_agent.py — Hello World example for microspade.

This program defines a single agent with two behaviours:
  * ``GreetBehaviour`` (OneShotBehaviour) – sends a greeting to itself
    and scrolls "Hello!" on the display.
  * ``ListenBehaviour`` (CyclicBehaviour) – waits for any incoming
    message and displays a happy face.

Flash this to one micro:bit and watch the display.
"""

from microbit import display, Image, sleep  # noqa: F401  (micro:bit builtins)
from microspade import Agent, CyclicBehaviour, OneShotBehaviour, Message


# ---------------------------------------------------------------------------
# Behaviours
# ---------------------------------------------------------------------------

class GreetBehaviour(OneShotBehaviour):
    """Send a greeting to self, then scroll 'Hello!' on the display."""

    def run(self):
        # Send a message to ourselves (local delivery, no radio needed)
        msg = Message(to=self.agent.name, body="Hello!", performative="inform")
        self.send(msg)
        display.scroll("Hello!")


class ListenBehaviour(CyclicBehaviour):
    """Display a happy face whenever a message arrives."""

    def run(self):
        msg = self.receive()
        if msg:
            display.show(Image.HAPPY)
            sleep(1000)
            display.clear()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class HelloAgent(Agent):
    def setup(self):
        self.add_behaviour(GreetBehaviour())
        self.add_behaviour(ListenBehaviour())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

agent = HelloAgent("hello_agent")
agent.run()   # blocks; press reset to stop
