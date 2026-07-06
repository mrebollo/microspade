"""
light_agent.py — Touch-controlled Light Agent and Artifact example.

This program defines a LightArtifact with operations to turn an LED display
on or off. A SwitchAgent focuses on the light, polls the physical micro:bit
touch logo (pin_logo) in a periodic behaviour to toggle the light, and reactively
receives notifications when the light state changes.
"""

from microbit import display, pin_logo
from ms_agent import Agent
from ms_artifact import Artifact
from ms_periodic import PeriodicBehaviour


# ---------------------------------------------------------------------------
# 1. Environment: Light Artifact
# ---------------------------------------------------------------------------

class LightArtifact(Artifact):
    """
    An artifact representing a light or LED.
    Exposes operations to turn it on or off.
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
        display.show(display.HEART)  # Show heart icon when on

    def turn_off(self):
        """Operation to turn the light OFF."""
        self.update_property("light_on", False)
        print("[Hardware] LED turned OFF")
        display.clear()  # Clear display when off


# ---------------------------------------------------------------------------
# 2. Behaviours
# ---------------------------------------------------------------------------

class TouchListenerBehaviour(PeriodicBehaviour):
    """
    Periodically checks if the physical touch logo is pressed to toggle the light.
    """

    def __init__(self):
        # Poll touch sensor every 100ms for high responsiveness
        super().__init__(period=0.1)
        self._was_touched = False

    def was_logo_touched(self):
        """
        Helper method to detect the rising edge (transition from False to True)
        of the physical touch logo, preventing rapid-fire multiple toggles.
        """
        current = pin_logo.is_touched()
        touched = current and not self._was_touched
        self._was_touched = current
        return touched

    def run(self):
        if self.was_logo_touched():
            if self.agent.get("light_on"):
                self.agent.light.turn_off()
            else:
                self.agent.light.turn_on()


# ---------------------------------------------------------------------------
# 3. Agent: Switch Agent
# ---------------------------------------------------------------------------

class SwitchAgent(Agent):
    def __init__(self, name, light_artifact, **kwargs):
        super().__init__(name, **kwargs)
        self.light = light_artifact

    def setup(self):
        # 1. Focus on the light artifact to receive its property updates
        self.focus(self.light)
        
        # 2. Add behaviour to listen for touch events
        self.add_behaviour(TouchListenerBehaviour())

    def on_light_on_change(self, value, artifact_name):
        # Triggered automatically when the physical 'light_on' property changes
        print("SwitchAgent: Light property is now", value)


# ---------------------------------------------------------------------------
# 4. Main Execution
# ---------------------------------------------------------------------------

# Create the light artifact
light_device = LightArtifact()

# Create the agent, passing the artifact reference
agent = SwitchAgent("switch", light_device)

# Start the agent and enter the main loop
agent.run()
