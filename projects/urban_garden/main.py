"""
projects/urban_garden/main.py

Urban Garden (Huerto Urbano) Agent and Artifacts implementation.
Reads soil moisture, ambient light, and temperature to decide when
to open a water valve using a servo motor.
"""

from microbit import display, pin1, pin2, temperature
from microspade import Agent, Artifact, PeriodicBehaviour


# ---------------------------------------------------------------------------
# 1. Artifacts
# ---------------------------------------------------------------------------

class SoilMoistureSensor(Artifact):
    """
    Artifact representing the soil moisture sensor.
    Connected to Pin 1 (Analog input).
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.define_property("moisture", 500)  # Range 0 (dry) to 1023 (wet)

    def read_sensor(self):
        """Read the sensor value."""
        val = pin1.read_analog()
        self.update_property("moisture", val)


class EnvironmentSensor(Artifact):
    """
    Artifact wrapping the micro:bit's built-in temperature and light level sensors.
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.define_property("temperature", 22)
        self.define_property("light_level", 120)  # Range 0 (dark) to 255 (bright)

    def read_sensors(self):
        self.update_property("temperature", temperature())
        self.update_property("light_level", display.read_light_level())


class WaterValve(Artifact):
    """
    Artifact managing a servo motor connected to Pin 2 as a water valve.
    Exposes operations to open or close the valve.
    """

    def __init__(self, name=None):
        super().__init__(name)
        self.define_property("valve_open", False)
        # Standard servo uses 50Hz (20ms period)
        pin2.set_analog_period(20)
        # Make sure it starts closed
        pin2.write_analog(51)  # ~1ms pulse (0 degrees / closed)

    # --- OPERATIONS ---

    def open_valve(self):
        """Operation to open the water valve (rotate servo to 90 degrees)."""
        self.update_property("valve_open", True)
        print("[Actuator] Opening valve (Servo 90 degrees)")
        pin2.write_analog(77)  # ~1.5ms pulse (90 degrees)
        display.show(display.ARROW_S)  # Down arrow (water flowing)

    def close_valve(self):
        """Operation to close the water valve (rotate servo to 0 degrees)."""
        self.update_property("valve_open", False)
        print("[Actuator] Closing valve (Servo 0 degrees)")
        pin2.write_analog(51)  # ~1ms pulse (0 degrees)
        display.clear()


# ---------------------------------------------------------------------------
# 2. Agent & Behaviours
# ---------------------------------------------------------------------------

class SensorPoller(PeriodicBehaviour):
    """
    A behavior to tick/read environmental artifacts.
    Since analog sensors on micro:bit don't support hardware interrupts,
    we poll them inside a periodic behavior.
    """

    def __init__(self, moisture_art, env_art, period=2.0):
        super().__init__(period)
        self.moisture_art = moisture_art
        self.env_art = env_art

    def run(self):
        self.moisture_art.read_sensor()
        self.env_art.read_sensors()


class GardenAgent(Agent):
    def setup(self):
        # Focus on all artifacts by name to resolve them
        self.moisture_art = self.focus("soil_moisture")
        self.env_art = self.focus("environment")
        self.valve = self.focus("water_valve")

        # Periodically poll the physical sensors
        self.add_behaviour(SensorPoller(self.moisture_art, self.env_art, period=2.0))

    # --- REACTIVE CALLBACKS ---

    def on_moisture_change(self, value, artifact_name):
        self.check_irrigation()

    def on_light_level_change(self, value, artifact_name):
        self.check_irrigation()

    def on_temperature_change(self, value, artifact_name):
        self.check_irrigation()

    def check_irrigation(self):
        """
        Decision logic triggered reactively when environmental properties change.
        """
        moisture = self.get("moisture")
        light = self.get("light_level")
        valve_open = self.get("valve_open")

        if moisture is None or light is None:
            return

        print("GardenAgent Check: Moisture={}, Light={}, ValveOpen={}".format(
            moisture, light, valve_open
        ))

        # Irrigation Logic:
        # - Water when soil is dry (moisture < 350) and sun is low (light < 80)
        # - Stop watering if soil is sufficiently moist (moisture >= 600) or sun is high (light >= 150)
        if moisture < 350 and light < 80:
            if not valve_open:
                print("GardenAgent: Soil is dry & sun is low. Opening valve.")
                self.valve.open_valve()
        elif moisture >= 600 or (light >= 150 and valve_open):
            if valve_open:
                print("GardenAgent: Soil is moist or sun is high. Closing valve.")
                self.valve.close_valve()


# ---------------------------------------------------------------------------
# 3. Execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create the artifacts (which register themselves automatically)
    moisture_sensor = SoilMoistureSensor(name="soil_moisture")
    env_sensor = EnvironmentSensor(name="environment")
    valve_device = WaterValve(name="water_valve")

    # Initialize and run agent
    agent = GardenAgent("garden_controller")
    agent.run()
