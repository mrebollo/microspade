"""
timeout_agent.py — Timer example using a TimeoutBehaviour.

This program defines an agent that displays an icon when button A is pressed,
and schedules a TimeoutBehaviour to automatically turn it off after 3 seconds.
"""

from microbit import display, Image, button_a
from ms_agent import Agent
from ms_cyclic import CyclicBehaviour
from ms_timeout import TimeoutBehaviour


class AutoOffBehaviour(TimeoutBehaviour):
    """Turns off the display when the timeout expires."""

    def run(self):
        display.clear()
        print("Timeout triggered: Display cleared")


class ButtonListenerBehaviour(CyclicBehaviour):
    """Listens for button A presses to show a heart and start the timer."""

    def run(self):
        spade = Image("00900:"
                      "09990:"
                      "99999:"
                      "00900:"
                      "09990"),
        if button_a.was_pressed():
            display.show(spade)
            print("Button A pressed: Show SPADE, starting 3s timer...")
            
            # Programar el auto-apagado a los 3 segundos
            self.agent.add_behaviour(AutoOffBehaviour(timeout=3.0))


class TimerAgent(Agent):
    def setup(self):
        self.add_behaviour(ButtonListenerBehaviour())


agent = TimerAgent("timer_agent")
agent.run()
