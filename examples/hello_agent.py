"""
simple_agent.py — Hello World example for microspade.

This program defines a single agent with a OneShotBehaviour that
prints a message to the serial console and scrolls it on the display.
"""

from microbit import display
from ms_agent import Agent
from ms_oneshot import OneShotBehaviour


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class GreetBehaviour(OneShotBehaviour):
    """Prints 'Hello, microspade!' to serial and scrolls it on the display."""

    def run(self):
        msg = "Hello, microspade!"
        print(msg)
        display.scroll(msg)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class HelloAgent(Agent):
    def setup(self):
        self.add_behaviour(GreetBehaviour())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

agent = HelloAgent("hello_agent")
agent.run()   # blocks; press reset to stop
