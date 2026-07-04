"""
projects/urban_garden/main.py

Urban Garden (Huerto Urbano) Agent and Artifacts implementation.
Reads soil moisture, ambient light, and temperature to decide when
to open a water valve using a servo motor.
"""

# Try importing microbit modules, fallback to mock if running on PC
try:
    from microbit import display, sleep, pin1, pin2, temperature, display
    # We will use:
    # - pin1 for Soil Moisture Sensor (Analog Read)
    # - pin2 for Servo Motor Valve (PWM Analog Write)
    HAS_MICROBIT = True
except ImportError:
    HAS_MICROBIT = False

from microspade import Agent, Artifact, PeriodicBehaviour, container


# ---------------------------------------------------------------------------
# 1. Artifacts
# ---------------------------------------------------------------------------

class SoilMoistureSensor(Artifact):
    """
    Artifact representing the soil moisture sensor.
    Connected to Pin 1 (Analog input).
    """

    def __init__(self):
        super().__init__()
        self.define_property("moisture", 500)  # Range 0 (dry) to 1023 (wet)

    def read_sensor(self):
        """Read the physical/simulated sensor value."""
        if HAS_MICROBIT:
            val = pin1.read_analog()
        else:
            # Simulate slight drying over time
            val = self._properties["moisture"] - 20
            if val < 200:
                val = 200  # clamp
        self.update_property("moisture", val)


class EnvironmentSensor(Artifact):
    """
    Artifact wrapping the micro:bit's built-in temperature and light level sensors.
    """

    def __init__(self):
        super().__init__()
        self.define_property("temperature", 22)
        self.define_property("light_level", 120)  # Range 0 (dark) to 255 (bright)

    def read_sensors(self):
        if HAS_MICROBIT:
            temp = temperature()
            light = display.read_light_level()
        else:
            # Simulate stable room temp and changing light (day/night cycle)
            temp = 22
            light = self._properties["light_level"] - 15
            if light < 20:
                light = 200  # Cycle back to daytime
        self.update_property("temperature", temp)
        self.update_property("light_level", light)


class WaterValve(Artifact):
    """
    Artifact managing a servo motor connected to Pin 2 as a water valve.
    Exposes operations to open or close the valve.
    """

    def __init__(self):
        super().__init__()
        self.define_property("valve_open", False)
        if HAS_MICROBIT:
            # Standard servo uses 50Hz (20ms period)
            pin2.set_analog_period(20)
            # Make sure it starts closed
            pin2.write_analog(51)  # ~1ms pulse (0 degrees / closed)

    # --- OPERATIONS ---

    def open_valve(self):
        """Operation to open the water valve (rotate servo to 90 degrees)."""
        self.update_property("valve_open", True)
        print("[Actuator] Opening valve (Servo 90 degrees)")
        if HAS_MICROBIT:
            pin2.write_analog(77)  # ~1.5ms pulse (90 degrees)
            display.show(display.ARROW_S)  # Down arrow (water flowing)

    def close_valve(self):
        """Operation to close the water valve (rotate servo to 0 degrees)."""
        self.update_property("valve_open", False)
        print("[Actuator] Closing valve (Servo 0 degrees)")
        if HAS_MICROBIT:
            pin2.write_analog(51)  # ~1ms pulse (0 degrees)
            display.clear()


# ---------------------------------------------------------------------------
# 2. Agent & Behaviours
# ---------------------------------------------------------------------------

class SensorPoller(PeriodicBehaviour):
    """
    A behavior to tick/read environmental artifacts.
    Note: In a true A&A architecture, the artifacts themselves could run on a
    hardware timer, but in MicroPython we poll them inside a periodic behavior.
    """

    def __init__(self, moisture_art, env_art, period=3.0):
        super().__init__(period)
        self.moisture_art = moisture_art
        self.env_art = env_art

    def run(self):
        self.moisture_art.read_sensor()
        self.env_art.read_sensors()


class IrrigationBrain(PeriodicBehaviour):
    """
    Decision behavior that reads the current environment properties from the
    agent KB (automatically synced via focus) and controls the valve.
    """

    def run(self):
        # 1. Read parameters from KB
        moisture = self.agent.get("moisture")
        light = self.agent.get("light_level")
        temp = self.agent.get("temperature")
        valve_open = self.agent.get("valve_open")

        print("Brain KB: Moisture={}, Light={}, Temp={}, ValveOpen={}".format(
            moisture, light, temp, valve_open
        ))

        # 2. Irrigation Logic:
        # - Water when soil is dry (moisture < 350)
        # - Preferably water when light level is low (light < 80) to avoid evaporation
        # - Stop watering if soil is sufficiently moist (moisture >= 600)
        
        valve = self.agent.valve

        if moisture < 350 and light < 80:
            if not valve_open:
                print("Brain: Soil is dry & sun is low. Opening valve.")
                valve.open_valve()
        elif moisture >= 600 or (light >= 150 and valve_open):
            if valve_open:
                print("Brain: Soil is moist or sun is high. Closing valve.")
                valve.close_valve()


class GardenAgent(Agent):
    def __init__(self, name, moisture_art, env_art, valve_art, **kwargs):
        super().__init__(name, **kwargs)
        self.moisture_art = moisture_art
        self.env_art = env_art
        self.valve = valve_art

    def setup(self):
        # Focus on all artifacts to receive their updates in KB
        self.focus(self.moisture_art)
        self.focus(self.env_art)
        self.focus(self.valve)

        # Add behaviors
        self.add_behaviour(SensorPoller(self.moisture_art, self.env_art, period=2.0))
        self.add_behaviour(IrrigationBrain(period=2.0))


# ---------------------------------------------------------------------------
# 3. Execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create the artifacts
    moisture_sensor = SoilMoistureSensor()
    env_sensor = EnvironmentSensor()
    valve = WaterValve()

    # Register them in the local container
    container.register_artifact("soil_moisture", moisture_sensor)
    container.register_artifact("environment", env_sensor)
    container.register_artifact("water_valve", valve)

    # Initialize agent (with dummy transport for PC run)
    if HAS_MICROBIT:
        agent = GardenAgent("garden_controller", moisture_sensor, env_sensor, valve)
    else:
        class DummyTransport:
            def setup(self): pass
            def teardown(self): pass
            def send(self, data): pass
            def receive(self): return None
            
        agent = GardenAgent("garden_controller", moisture_sensor, env_sensor, valve, transport=DummyTransport())

    # Start the agent
    agent.start()

    print("Urban Garden controller starting... (Press Ctrl+C to exit)")
    try:
        # Run 6 cycles to show simulation
        for cycle in range(6):
            agent.step()
            
            # If running in simulation, artificially force a dry & dark state to trigger watering
            if not HAS_MICROBIT and cycle == 2:
                print("\n--- SIMULATION: Forcing dry & dark environment ---")
                moisture_sensor.update_property("moisture", 300)
                env_sensor.update_property("light_level", 50)
                print("--------------------------------------------------\n")
                
            if HAS_MICROBIT:
                sleep(2000)
            else:
                import time
                time.sleep(2.0)
    finally:
        agent.stop()
        print("Controller stopped.")
