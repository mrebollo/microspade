# projects/cutebot_controller/main.py
"""
Cutebot Controller Project

An autonomous robot controller using microspade agents to drive the
Elecfreaks Cutebot smart car.

Tasks to implement later:
1. Initialize the Cutebot I2C connections and pins.
2. Read ultrasonic distance and line tracker sensors periodically.
3. Decouple decision making (BDI behaviours / FSM) from hardware actuators.
4. Drive motors via I2C commands in a dedicated Actuator behavior.
"""

from microbit import *
# Import microspade components (once flashed/uploaded)
from microspade import Agent, CyclicBehaviour, PeriodicBehaviour, FSMBehaviour, State

# Cutebot Hardware Constants
CUTEBOT_ADDR = 0x10
LEFT_MOTOR = 0x01
RIGHT_MOTOR = 0x02

# Direction Codes
DIR_FORWARD = 0x02
DIR_BACKWARD = 0x01


# ---------------------------------------------------------------------------
# Behaviours: Sensors (Input)
# ---------------------------------------------------------------------------

class SensorReader(PeriodicBehaviour):
    """
    Reads hardware sensors (ultrasonic sonar and line tracking) periodically
    and updates the agent's Knowledge Base (KB).
    """

    def __init__(self, period=0.1):
        super().__init__(period)
        # TODO: Initialize sensor pin modes (P8 Trigger, P12 Echo, P13/P14 Line sensors)

    def run(self):
        # TODO: 
        # 1. Read ultrasonic distance (using trigger pulse and time_pulse_us)
        # 2. Read left (P13) and right (P14) infrared line sensors
        # 3. Store readings in KB (e.g., self.agent.set("distance", dist), self.agent.set("line", tracking))
        pass


# ---------------------------------------------------------------------------
# Behaviours: Actuators (Output)
# ---------------------------------------------------------------------------

class MotorActuator(PeriodicBehaviour):
    """
    Reads target motor speeds from the agent's KB and writes the corresponding
    I2C commands to the Cutebot's motor control board.
    """

    def __init__(self, period=0.05):
        super().__init__(period)
        # TODO: Initialize I2C connection

    def run(self):
        # TODO:
        # 1. Retrieve target speeds from KB (e.g., self.agent.get("left_speed"), self.agent.get("right_speed"))
        # 2. Send I2C write frames:
        #    Left:  [0x01, direction, absolute_speed, 0]
        #    Right: [0x02, direction, absolute_speed, 0]
        # 3. Stop car if no speed values are set
        pass


# ---------------------------------------------------------------------------
# Behaviours: Decision Making (Brain)
# ---------------------------------------------------------------------------

class AvoidObstacles(CyclicBehaviour):
    """
    Simple obstacle avoidance logic. If an obstacle is detected within
    a threshold distance, it overrides standard navigation to turn or reverse.
    """

    def run(self):
        # TODO:
        # 1. Read 'distance' from KB.
        # 2. If distance is too small, set low/reverse/turning speeds in KB.
        # 3. Otherwise, defer speed control to other behaviors or default forward.
        # 4. Use yield to prevent busy waiting.
        yield 0.05


class FollowLine(CyclicBehaviour):
    """
    Line following behavior using the infrared sensor readings in the KB.
    """

    def run(self):
        # TODO:
        # 1. Read 'line' state from KB.
        # 2. Adjust target left_speed and right_speed in KB to stay centered on line.
        # 3. Yield to let other behaviors run.
        yield 0.05


# ---------------------------------------------------------------------------
# Agent Definition
# ---------------------------------------------------------------------------

class CutebotAgent(Agent):
    """
    Main agent that orchestrates the Cutebot sensor readings, decision loop,
    and motor controller output.
    """

    def setup(self):
        # Add Input behaviors
        self.add_behaviour(SensorReader(period=0.1))

        # Add Output behaviors
        self.add_behaviour(MotorActuator(period=0.05))

        # Add Decision (Brain) behaviors
        self.add_behaviour(AvoidObstacles())
        # self.add_behaviour(FollowLine()) # Can be toggled or combined

        # Initialize KB default values
        self.set("left_speed", 0)
        self.set("right_speed", 0)
        self.set("distance", 100)


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create and run the agent
    agent = CutebotAgent("cutebot")
    # agent.run()
