"""
fsm_agent.py — Finite State Machine behaviour example.

This example demonstrates ``FSMBehaviour`` with three states that cycle
through LED display patterns in response to button presses.

States
------
IDLE     – display heart, wait for button A press → ACTIVE
ACTIVE   – display arrow, send broadcast, wait for button B press → DONE
DONE     – display check mark, stop the FSM

Flash this to a single micro:bit.
"""

from microbit import display, Image, button_a, button_b
from microspade import Agent, FSMBehaviour, State, Message

# State name constants
IDLE = "IDLE"
ACTIVE = "ACTIVE"
DONE = "DONE"


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class IdleState(State):
    """Show heart icon; transition to ACTIVE when button A is pressed."""

    def on_start(self):
        display.show(Image.HEART)

    def run(self):
        if button_a.was_pressed():
            self.set_next_state(ACTIVE)


class ActiveState(State):
    """Show arrow icon, broadcast an alert; transition to DONE on button B."""

    def on_start(self):
        display.show(Image.ARROW_E)
        # Broadcast to all listening agents on the same channel
        self.send(Message(to="*", body="activated", performative="inform"))

    def run(self):
        if button_b.was_pressed():
            self.set_next_state(DONE)

    def on_end(self):
        display.clear()


class DoneState(State):
    """Show a tick, then terminate the FSM."""

    def run(self):
        display.show(Image.YES)
        yield 2.0
        display.clear()
        self.kill()  # terminal state — ends the FSM


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class DisplayAgent(Agent):
    def setup(self):
        fsm = FSMBehaviour()
        fsm.add_state(IDLE, IdleState(), initial=True)
        fsm.add_state(ACTIVE, ActiveState())
        fsm.add_state(DONE, DoneState())

        fsm.add_transition(IDLE, ACTIVE)
        fsm.add_transition(ACTIVE, DONE)

        self.add_behaviour(fsm)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

agent = DisplayAgent("display_agent")
agent.run()
