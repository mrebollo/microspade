"""
artifact_agent.py — Example demonstrating microspade Artifacts.

This program defines a simulated temperature sensor artifact and an agent
that focuses on it. The agent automatically receives temperature updates
in its Knowledge Base (KB) and displays them without polling the sensor directly.
"""

# Try importing microbit modules, fallback to mock if running on PC
try:
    from microbit import display, sleep
    import music
    HAS_MICROBIT = True
except ImportError:
    HAS_MICROBIT = False

from microspade import Agent, Artifact, PeriodicBehaviour


# ---------------------------------------------------------------------------
# 1. Environment: Temperature Sensor Artifact
# ---------------------------------------------------------------------------

class TemperatureSensor(Artifact):
    """
    A simulated temperature sensor.
    """

    def __init__(self):
        super().__init__()
        # Define the initial temperature property
        self.define_property("temperature", 20)
        self._trend = 1

    def simulate_read(self):
        """Simulate reading a new temperature value from the sensor."""
        current_temp = self._properties["temperature"]
        
        # Fluctuate temperature between 18 and 25 degrees
        if current_temp >= 25:
            self._trend = -1
        elif current_temp <= 18:
            self._trend = 1
            
        next_temp = current_temp + self._trend
        self.update_property("temperature", next_temp)


# ---------------------------------------------------------------------------
# 2. Agent: Thermostat Agent
# ---------------------------------------------------------------------------

class DisplayBehaviour(PeriodicBehaviour):
    """
    Periodically checks the agent's Knowledge Base for the current temperature
    and outputs it. This behaviour has no direct connection to the sensor.
    """

    def run(self):
        # The agent's KB is updated automatically because the agent is focusing
        # on the TemperatureSensor artifact.
        temp = self.agent.get("temperature")
        
        print("Agent KB: temperature =", temp)
        
        if HAS_MICROBIT:
            # Show a simple threshold warning on the LED display
            if temp > 22:
                display.scroll("HOT:{}C".format(temp), delay=80)
                music.pitch(660, 100)
            else:
                display.scroll("{}C".format(temp), delay=80)


class ThermostatAgent(Agent):
    def __init__(self, name, sensor_artifact, **kwargs):
        super().__init__(name, **kwargs)
        self.sensor = sensor_artifact

    def setup(self):
        # 1. Focus on the temperature sensor to observe its properties
        self.focus(self.sensor)
        
        # 2. Add behaviour to periodically show the current reading
        self.add_behaviour(DisplayBehaviour(period=2.0))


# ---------------------------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------------------------

# Create the environment artifact
sensor = TemperatureSensor()

# Create the agent and pass the artifact reference
if HAS_MICROBIT:
    agent = ThermostatAgent("thermostat", sensor)
else:
    class DummyTransport:
        def setup(self):
            pass
        def teardown(self):
            pass
        def send(self, data):
            pass
        def receive(self):
            return None
            
    agent = ThermostatAgent("thermostat", sensor, transport=DummyTransport())

# Start the agent (non-blocking setup)
agent.start()


# Main loop to simulate environment changes and run agent cycles
print("Starting simulation... (Press Ctrl+C to exit)")
try:
    # Run for a few cycles
    for cycle in range(10):
        # 1. Simulate the sensor reading a new value
        sensor.simulate_read()
        
        # 2. Execute agent behaviors
        agent.step()
        
        # Wait 1 second between cycles
        if HAS_MICROBIT:
            sleep(1000)
        else:
            import time
            time.sleep(1.0)
finally:
    agent.stop()
    print("Simulation finished.")
