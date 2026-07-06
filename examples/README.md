# examples — microspade

These are ready-to-use examples for micro:bit.
Flash any of them with the [micro:bit Python editor](https://python.microbit.org/)
or with the [uflash](https://uflash.readthedocs.io/) command-line tool.

Make sure to upload the modular `ms_*.py` files required by the example (e.g., `ms_agent.py`, `ms_behaviour.py`) to the board alongside the example script.

| File | Description |
|------|-------------|
| `hello_agent.py` | Simple agent that prints a greeting and scrolls it on the display using `OneShotBehaviour` |
| `counter_agent.py` | Countdown timer with voice synthesis (micro:bit V2) and a rocket launch animation using `CyclicBehaviour` |
| `periodic_agent.py` | Toggles a corner LED and plays a beep periodically using `PeriodicBehaviour` |
| `timeout_agent.py` | Displays an icon and clears it automatically after 3 seconds using `TimeoutBehaviour` |
| `fsm_agent.py` | FSM behaviour that cycles through LED patterns in response to button presses |
| `ping_pong.py` | Two boards exchanging ping/pong messages over the radio transport |
| `artifact_agent.py` | Temperature sensor artifact focused by an agent to reactively update the LED display |
| `rain_sensor_agent.py` | Hardware-interrupt driven rain warning sensor artifact and reactive agent callback |
| `light_agent.py` | Touch logo switch toggling a light artifact with reactive state-change notifications |
