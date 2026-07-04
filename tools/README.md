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
