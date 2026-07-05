"""
rain_sensor_agent.py — Hardware-interrupt rain warning example using machine.Pin.

This example shows how an Artifact handles low-level hardware interrupts to
update its properties, and how the Agent reactively responds to the changes
using dynamic convention-based callbacks, avoiding any polling behaviour.
"""

from microbit import display
import machine
from microspade import Agent, Artifact


# ---------------------------------------------------------------------------
# 1. Environment: Interrupt-Driven Rain Sensor Artifact
# ---------------------------------------------------------------------------

class RainSensorArtifact(Artifact):
    """
    Encapsulates a digital rain sensor.
    Uses machine.Pin interrupts to achieve 100% event-driven updates.
    """

    def __init__(self, name=None, pin_number=8):
        super().__init__(name)
        self.define_property("raining", False)
        
        # Configure the GPIO pin via machine module
        self._pin = machine.Pin(pin_number, machine.Pin.IN, machine.Pin.PULL_DOWN)
        
        # Attach a hardware interrupt handler (ISR)
        # Triggers on both rising (0->1: rain started) and falling (1->0: rain stopped) edges
        self._pin.irq(
            handler=self._hardware_isr,
            trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING
        )

    def _hardware_isr(self, pin):
        """
        Interrupt Service Routine (ISR) executed by the CPU.
        Runs immediately when the hardware pin changes voltage.
        """
        self.update_property("raining", bool(pin.value()))


# ---------------------------------------------------------------------------
# 2. Agent
# ---------------------------------------------------------------------------

class WeatherAgent(Agent):
    def setup(self):
        # Focus on the rain sensor by its name
        self.focus("rain_sensor")

    def on_raining_change(self, value, artifact_name):
        # Triggered automatically when the physical 'raining' property changes
        if value:
            print("Agent Alert: It is raining! Open the umbrella!")
            display.show(display.UMBRELLA)
        else:
            print("Agent Alert: Rain has stopped. Clear sky.")
            display.show(display.HAPPY)


# ---------------------------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------------------------

# Create the artifact (passing its registered name)
sensor = RainSensorArtifact(name="rain_sensor")

# Initialize and start agent
agent = WeatherAgent("weather_agent")

# Run the agent in the main loop
agent.run()
