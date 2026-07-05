# Environmental Monitor

This project implements an intelligent, autonomous environmental monitor designed to run on a single **BBC micro:bit (V2)** board using the **Microspade** framework.

The system concurrently monitors temperature, light, and sound levels, evaluates the comfort level of the room, and provides visual and interactive feedback to the user.

---

## Key Features

1.  **Concurrent Sensor Reading:**
    *   **Temperature:** Uses the built-in processor temperature sensor.
    *   **Light:** Reads the ambient light level using the LED matrix.
    *   **Sound:** Measures surrounding decibels using the built-in microphone (requires micro:bit V2).
2.  **Data Logging:** Persists the history of the agent's knowledge base (`KB`) state directly into the board's flash memory.
3.  **Visual Comfort Indicator:**
    *   💤 **Sleepy Face (`Image.ASLEEP`):** Triggered when it is dark (light level < 15), representing night mode.
    *   ❌ **Warning Cross (`Image.NO`):** Triggered when sound levels exceed 120 (too noisy).
    *   🙁 **Sad Face (`Image.SAD`):** Triggered when temperature is outside the comfort range of 18°C to 27°C.
    *   🙂 **Happy Face (`Image.HAPPY`):** Displayed when all conditions are within optimal levels.
4.  **Interactive Query:** Pressing **Button A** triggers a high beep and scrolls the exact readings (e.g., `T:22C L:105 S:35`) across the LED screen.

---

## Agent Architecture and Behaviours

The project utilizes a single agent named `EnvironmentalAgent` that schedules three concurrent, non-blocking behaviours using the **Microspade** cooperative scheduler:

*   **`SensorReader` (PeriodicBehaviour - every 2.0s):** Polls physical sensors and updates the agent's KB via `self.agent.set()`. It also flushes the state to the flash memory log.
*   **`ComfortIndicator` (CyclicBehaviour - reactive):** Evaluates the comfort thresholds from the KB and updates the LED matrix. It uses `yield 0.5` to yield control cooperatively.
*   **`ButtonListener` (CyclicBehaviour - interactive):** Listens for Button A presses. It uses `yield 0.05` for high polling responsiveness without blocking other agent operations.

---

## Project Structure

*   `main.py`: The pure Python entry point for the micro:bit containing the behaviours, agent definition, and startup loop.
*   `README.md`: This explanatory file.

---

## Getting Started

1.  Make sure the compiled framework library `microspade.py` (found in `dist/microspade.py`) is uploaded to your micro:bit.
2.  Upload `main.py` to your micro:bit using your preferred utility (e.g., `microfs` or the official online Micro:bit editor).
3.  Connect to the board over a serial console to view real-time logs and agent print outputs.
