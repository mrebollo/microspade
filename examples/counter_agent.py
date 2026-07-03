"""
counter_agent.py — Countdown example using a CyclicBehaviour.

This program defines an agent with a CyclicBehaviour that counts down
from a start value (default 9) to 0. It displays each number, prints it
to the serial console, and plays a rocket launch animation when the countdown ends.
"""

from microbit import display, Image, sleep
from microspade import Agent, CyclicBehaviour


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

class CountdownBehaviour(CyclicBehaviour):
    """Counts down from a starting value, printing and displaying the count."""

    def __init__(self, start_value=9):
        super().__init__()
        self.counter = start_value

    def run(self):
        if self.counter >= 0:
            print(self.counter)
            display.show(str(self.counter))
            sleep(1000)  # Wait 1 second between numbers
            self.counter -= 1
        else:
            #print("Blastoff!")
            
            # Custom frames for a rocket taking off upwards
            rocket_frames = [
                Image("00000:"
                      "00000:"
                      "00900:"
                      "00900:"
                      "09990"),
                Image("00000:"
                      "00900:"
                      "00900:"
                      "09990:"
                      "00550"),
                Image("00900:"
                      "00900:"
                      "09990:"
                      "00550:"
                      "05500"),
                Image("00900:"
                      "09990:"
                      "05500:"
                      "00550:"
                      "00500"),
                Image("09990:"
                      "00550:"
                      "05500:"
                      "00500:"
                      "00000"),
                Image("05500:"
                      "00550:"
                      "00500:"
                      "00000:"
                      "00000"),
                Image("00550:"
                      "00500:"
                      "00000:"
                      "00000:"
                      "00000"),
                Image("00500:"
                      "00000:"
                      "00000:"
                      "00000:"
                      "00000")
            ]
            
            # Play animation with 150ms between frames
            display.show(rocket_frames, delay=150)
            
            self.kill()       # Terminate the cyclic behaviour
            self.agent.stop()  # Stop the agent loop


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CounterAgent(Agent):
    def setup(self):
        self.add_behaviour(CountdownBehaviour(start_value=9))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

agent = CounterAgent("counter_agent")
agent.run()   # blocks; press reset to stop
