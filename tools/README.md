# PC Development Tools for Microspade

This directory contains utility scripts that run on the development computer (PC) to support building, flashing, and receiving telemetry from Microspade agents running on the BBC micro:bit.

---

## 1. `build_module.py` — Library Bundler

The BBC micro:bit Python Editor and other flashing tools require dependencies to be either uploaded as files or bundled into a single executable file. `build_module.py` compiles the source files of the `microspade` directory into a single, optimized `microspade.py` library.

### Usage
Run this script from the repository root:
```bash
python3 tools/build_module.py
```
or 
```bash
uv run tools/build_module.py 
```

This will:
1. Parse the `microspade` module directory.
2. Concatenate and optimize (minify docstrings) the files.
3. Output the single-file library to `dist/microspade.py`.
4. Output the same file directly to `examples/microspade.py` so examples can be easily ran/packaged.

---

## 2. `receiver.py` — Generic Telemetry Receiver

This script connects to a micro:bit via USB Serial (UART) and captures telemetry data in real-time. It automatically parses any agent's knowledge base output (using the pythonic `print(agent)`) and writes it to a local CSV file.

### Requirements
Install the `pyserial` dependency on your computer:
```bash
pip install pyserial
# or using uv:
uv pip install pyserial
```

### Usage
1. Connect your micro:bit running a Microspade agent (with logging enabled) to your computer via USB.
2. Run the script from the repository root:
   ```bash
   python3 tools/receiver.py
   ```

### How it works:
* **Auto-Discovery:** It searches your computer's USB ports to find a device matching the official micro:bit Vendor ID (`0x0D28`).
* **Dynamic Inspection:** When it receives the first state message from an agent, it reads its keys dynamically (e.g. `temperature`, `light`, `sound`) and configures the table structure.
* **CSV Logging:** Saves all parsed data alongside computer-generated timestamps to a local `sensor_data.csv` file in the directory where you run the script. This file can be imported directly into Python (using Pandas/Scikit-Learn) for Machine Learning training.

---

## 3. `flash.sh` — Micro:bit Flasher

Copies `dist/microspade.py` and a user script to a connected BBC micro:bit V2 via USB.
Optionally downloads and flashes the MicroPython firmware if the board does not have it yet.

This tool supports both project-style (with `main.py` in a subdirectory) and example-style (standalone `.py` files) layouts.

### Requirements
- micro:bit V2 connected via USB (must appear as `/Volumes/MICROBIT`)
- `dist/microspade.py` must exist (run `build_module.py` first)

### Usage

**Flash a script** (micro:bit already has MicroPython):
```bash
bash tools/flash.sh examples/hello_agent.py
bash tools/flash.sh projects/cutebot_controller/
```

**Flash firmware + script** (first time, or after flashing a non-MicroPython hex):
```bash
bash tools/flash.sh examples/hello_agent.py --firmware
```

### Workflow
1. Resolves the main script from the given path (directory → `main.py`, file → used directly).
2. Verifies that `dist/microspade.py` exists and that the micro:bit is mounted.
3. With `--firmware`: downloads `micropython-v2.1.1.hex` from the Micro:bit Foundation GitHub releases (cached in `dist/` after the first download) and copies it to the board, then waits for reboot.
4. Copies `dist/microspade.py` to `/Volumes/MICROBIT/`.
5. Copies the main script as `main.py` to `/Volumes/MICROBIT/`.

The board runs `main.py` automatically on the next reset.
