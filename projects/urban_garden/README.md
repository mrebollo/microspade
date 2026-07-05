# Urban Garden (Huerto Urbano) Controller

This project implements an automated urban garden irrigation system on the micro:bit using the **Agents & Artifacts (A&A)** paradigm of `microspade`.

It monitors soil moisture, ambient light, and temperature, and automatically opens a gravity-fed water tank valve using a 180-degree servo motor.

---

## 1. Hardware Connection Layout

| Component | Pin on micro:bit | Type | Description |
|---|---|---|---|
| **Soil Moisture Sensor** | `Pin 1` | Analog Input | Reads moisture levels (0 = dry, 1023 = fully wet). |
| **Servo Motor (Valve)** | `Pin 2` | Analog Output (PWM) | Controls the water tank valve position (0° closed, 90° open). |
| **Light Sensor** | Built-in | Internal | Uses the LED matrix to detect light level (0 = dark, 255 = bright). |
| **Temp Sensor** | Built-in | Internal | Monitors MCU core temperature for frost alerts. |

### Servo Wiring
*   **Brown/Black:** GND
*   **Red:** VCC (3.3V or external 5V if using a larger servo)
*   **Orange/Yellow (Signal):** Connected to Pin 2

---

## 2. Software Architecture

This project strictly follows the **Agents & Artifacts (A&A)** architecture with event-driven, callback-based decision making:

```mermaid
graph TD
    subgraph Environment (Hardware & Artifacts)
        SM[SoilMoistureSensor Artifact]
        ES[EnvironmentSensor Artifact]
        WV[WaterValve Artifact]
    end

    subgraph Agent (Reasoning Loop)
        GA[GardenAgent]
        SP[SensorPoller Behaviour]
        KB[(Agent Knowledge Base)]
    end

    SM -- updates moisture property --> KB
    ES -- updates temperature/light property --> KB
    WV -- updates valve_open property --> KB
    GA -- focus --> SM
    GA -- focus --> ES
    GA -- focus --> WV
    SP -- polls every 2s --> SM
    SP -- polls every 2s --> ES
    KB -- triggers on_<prop>_change callbacks --> GA
    GA -- invokes open_valve/close_valve --> WV
```

*   **Artifacts:** Encapsulate the hardware layers (pin reads, PWM servo angles, internal sensor libraries). They expose **Observable Properties** (`moisture`, `temperature`, `light_level`, `valve_open`) and **Operations** (`open_valve()`, `close_valve()`).
*   **Agent Behaviours:**
    *   `SensorPoller`: A simple periodic behavior that prompts the sensors to take readings every 2 seconds.
*   **Reactive Decision Making:** The `GardenAgent` listens for property updates in the KB via `on_moisture_change`, `on_light_level_change`, and `on_temperature_change` callbacks. Whenever any of these trigger, the agent immediately runs `check_irrigation()` to decide whether to open or close the valve.

---

## 3. Irrigation Logic

To conserve water and prevent leaf burns, the system applies these rules:
1.  **Irrigation Trigger:** Soil moisture drops below `350` **and** the ambient light level is below `80` (dusk/nighttime).
2.  **Irrigation Stop:** Soil moisture reaches `600` **or** the light level goes above `150` (daytime/sun rises, indicating a timeout or weather change).

---

## 4. How to Deploy

1.  Open the [micro:bit Python Editor V3](https://python.microbit.org/v/3).
2.  Drag and drop the bundled library file `dist/microspade.py` into the editor's file list.
3.  Copy the code from `projects/urban_garden/main.py` into your `main.py` script.
4.  Flash it to your micro:bit V2 board.
