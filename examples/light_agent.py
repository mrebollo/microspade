"""
light_agent.py — Simple example demonstrating Artifact Operations.

This program defines a LightArtifact with operations to turn a light on or off.
A SwitchAgent focuses on the light and periodically toggles its state
by invoking these operations.
"""

# Try importing microbit modules, fallback to mock if running on PC
try:
    from microbit import display, sleep
    HAS_MICROBIT = True
except ImportError:
    HAS_MICROBIT = False

from microspade import Agent, Artifact, PeriodicBehaviour


# ---------------------------------------------------------------------------
# 1. Environment: Light/LED Artifact
# ---------------------------------------------------------------------------

class LightArtifact(Artifact):
    """
    An artifact representing a light or LED.
    It exposes operations to turn it on or off.
    """

    def __init__(self):
        super().__init__()
        # Define the observable property
        self.define_property("light_on", False)

    # --- OPERATIONS ---

    def turn_on(self):
        """Operation to turn the light ON."""
        self.update_property("light_on", True)
        print("[Hardware] LED turned ON")
        if HAS_MICROBIT:
            display.show(display.HEART)  # Show heart icon when on

    def turn_off(self):
        """Operation to turn the light OFF."""
        self.update_property("light_on", False)
        print("[Hardware] LED turned OFF")
        if HAS_MICROBIT:
            display.clear()  # Clear display when off


# ---------------------------------------------------------------------------
# 2. Agent: Switch Agent
# ---------------------------------------------------------------------------

class ToggleBehaviour(PeriodicBehaviour):
    """
    Periodically checks the current state of the light in the agent's KB,
    and toggles it by invoking the artifact's operations.
    """

    def run(self):
        # Read the current observable state from the KB (updated automatically)
        is_on = self.agent.get("light_on")
        
        print("Agent KB: light_on =", is_on)

        # Retrieve the artifact reference from the agent
        light = self.agent.light

        # Invoke the corresponding operation on the artifact
        if is_on:
            print("Agent: Invoking turn_off()")
            light.turn_off()
        else:
            print("Agent: Invoking turn_on()")
            light.turn_on()


class SwitchAgent(Agent):
    def __init__(self, name, light_artifact, **kwargs):
        super().__init__(name, **kwargs)
        self.light = light_artifact

    def setup(self):
        # 1. Focus on the light artifact to receive its property updates
        self.focus(self.light)
        
        # 2. Add behaviour to toggle the light every 2 seconds
        self.add_behaviour(ToggleBehaviour(period=2.0))


# ---------------------------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------------------------

# Create the physical/environment artifact
light_device = LightArtifact()

# Create the agent, passing the artifact reference
if HAS_MICROBIT:
    agent = SwitchAgent("switch", light_device)
else:
    class DummyTransport:
        def setup(self): pass
        def teardown(self): pass
        def send(self, data): pass
        def receive(self): return None
        
    agent = SwitchAgent("switch", light_device, transport=DummyTransport())

# Start the agent
agent.start()

print("Starting Switch Agent... (Press Ctrl+C to exit)")
try:
    # Run 6 cycles of the agent step loop
    for cycle in range(6):
        agent.step()
        
        # Wait 2 seconds (matching the behaviour period)
        if HAS_MICROBIT:
            sleep(2000)
        else:
            import time
            time.sleep(2.0)
finally:
    agent.stop()
    print("Agent stopped.")
