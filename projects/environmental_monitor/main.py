"""
main.py — Environmental monitor using built-in sensors.

This project runs a single agent on a BBC micro:bit board.
It reads temperature, ambient light, and sound levels (if micro:bit V2),
stores the data in the agent's knowledge base, and controls the LED matrix
to indicate comfort level.

Interactions:
- Screen: Shows a happy face if environment is comfortable, sad face if not,
          and a sleepy face if it is dark.
- Button A: Scrolls the exact sensor readings (e.g., "T:22C L:105 S:35").
"""

from microbit import display, Image, temperature, button_a, microphone
import music
from ms_agent import Agent
from ms_cyclic import CyclicBehaviour
from ms_periodic import PeriodicBehaviour
from ms_log import log_kb


# ---------------------------------------------------------------------------
# Behaviours
# ---------------------------------------------------------------------------

class SensorReader(PeriodicBehaviour):
    """
    Periodically polls the micro:bit physical sensors and updates
    the agent's knowledge base.
    """

    def __init__(self, period=2.0):
        super().__init__(period)

    def run(self):
        # Read sensors and update the agent's knowledge base (KB)
        self.agent.set("temperature", temperature())
        self.agent.set("light", display.read_light_level())
        self.agent.set("sound", microphone.sound_level())

        # Log agent state to flash memory
        log_kb(self.agent)

        # Print agent state to serial console
        print(self.agent)


class ComfortIndicator(CyclicBehaviour):
    """
    Analyzes environmental conditions from the knowledge base and
    updates the LED matrix to reflect the room comfort level.
    """

    def run(self):
        # Retrieve latest sensor data from the agent's KB
        temp = self.agent.get("temperature")
        light = self.agent.get("light")
        sound = self.agent.get("sound")

        # If data is not yet available, show a waiting animation
        if temp is None or light is None or sound is None:
            display.show(Image.CLOCK12)
            yield 0.1
            return

        # Determine comfort status
        # Thresholds:
        # - Noise: level > 120 is considered too noisy
        # - Temperature: comfort range is 18°C to 27°C
        # - Light: level < 15 is considered dark (night mode)
        
        if light < 15:
            # Night mode (low light) -> display sleepy face
            display.show(Image.ASLEEP)
        elif sound > 120:
            # Noise alert -> display warning cross
            display.show(Image.NO)
        elif temp < 18 or temp > 27:
            # Thermal discomfort -> display sad face
            display.show(Image.SAD)
        else:
            # All conditions comfortable -> display happy face
            display.show(Image.HAPPY)

        # Yield to scheduler for a short duration
        yield 0.5


class ButtonListener(CyclicBehaviour):
    """
    Listens for Button A presses to scroll the exact sensor
    readings across the LED display.
    """

    def run(self):
        if button_a.was_pressed():
            # Retrieve latest data
            temp = self.agent.get("temperature")
            light = self.agent.get("light")
            sound = self.agent.get("sound")

            if temp is not None:
                # Play a short high beep and scroll values
                music.pitch(1000, 50)
                info = "T:{}C L:{} S:{}".format(temp, light, sound)
                display.scroll(info, delay=80, wait=True)
            else:
                display.scroll("WAIT", delay=80, wait=True)

        # Yield to scheduler (poll at a responsive rate)
        yield 0.05


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class EnvironmentalAgent(Agent):
    def setup(self):
        # Add the three concurrent behaviours
        self.add_behaviour(SensorReader(period=2.0))
        self.add_behaviour(ComfortIndicator())
        self.add_behaviour(ButtonListener())
        
        print("Environmental Agent initialized and running!")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# Use a custom name for the agent and enable logging
agent = EnvironmentalAgent("comfort_monitor", enable_log=True)
agent.run()
