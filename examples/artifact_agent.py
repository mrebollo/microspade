"""
artifact_agent.py — Temperature Sensor Artifact and Agent example.

This program defines a TemperatureSensor artifact that reads the micro:bit's
built-in thermometer, and a ThermostatAgent that focuses on it and reactively
updates the display when the physical temperature changes.
"""

from microbit import display, temperature
import music
from microspade import Agent, Artifact, PeriodicBehaviour


# ---------------------------------------------------------------------------
# 1. Environment: Temperature Sensor Artifact
# ---------------------------------------------------------------------------

class TemperatureSensor(Artifact):
    """
    An artifact representing the built-in temperature sensor.
    """

    def __init__(self):
        super().__init__()
        # Initialise with the current physical temperature
        self.define_property("temperature", temperature())

    def read_sensor(self):
        """Read the actual hardware sensor and update the property."""
        self.update_property("temperature", temperature())


# ---------------------------------------------------------------------------
# 2. Agent: Thermostat Agent
# ---------------------------------------------------------------------------

class ReadSensorBehaviour(PeriodicBehaviour):
    """Periodically triggers the sensor artifact to read its physical value."""

    def run(self):
        self.agent.sensor.read_sensor()


class ThermostatAgent(Agent):
    def __init__(self, name, sensor_artifact, **kwargs):
        super().__init__(name, **kwargs)
        self.sensor = sensor_artifact

    def setup(self):
        # 1. Focus on the temperature sensor to observe its properties
        self.focus(self.sensor)
        
        # 2. Add behaviour to trigger sensor reads every 2 seconds
        self.add_behaviour(ReadSensorBehaviour(period=2.0))

    def on_temperature_change(self, value, artifact_name):
        # Triggered automatically when the physical 'temperature' property changes
        print("Temperature changed to:", value)
        
        # Show a simple warning if it gets too hot
        if value > 22:
            display.scroll("HOT:{}C".format(value), delay=80)
            music.pitch(660, 100)
        else:
            display.scroll("{}C".format(value), delay=80)


# ---------------------------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------------------------

# Create the physical sensor artifact
sensor = TemperatureSensor()

# Create the agent and pass the artifact reference
agent = ThermostatAgent("thermostat", sensor)

# Start the agent and enter the main loop
agent.run()
