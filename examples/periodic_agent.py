"""
periodic_agent.py — Periodic heartbeat beeper example.

This program defines an agent with a PeriodicBehaviour that triggers
every 3 seconds. It toggles the top-left corner LED and plays a beep.
"""

from microbit import display
import music
from ms_agent import Agent
from ms_periodic import PeriodicBehaviour


class BeaconBehaviour(PeriodicBehaviour):
    """Toggles a corner LED and plays a beep periodically."""

    def __init__(self, period=3.0):
        super().__init__(period)
        self.led_on = False

    def run(self):
        # Alternar estado del LED
        self.led_on = not self.led_on
        brightness = 9 if self.led_on else 0
        display.set_pixel(0, 0, brightness)
        
        # Tocar un tono de 880 Hz durante 100 ms
        music.pitch(880, 100)
        
        print("Tick! LED is", "ON" if self.led_on else "OFF")


class BeaconAgent(Agent):
    def setup(self):
        # Ejecuta el comportamiento cada 3.0 segundos
        self.add_behaviour(BeaconBehaviour(period=3.0))


agent = BeaconAgent("beacon_agent")
agent.run()
