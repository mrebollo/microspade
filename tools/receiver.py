#!/usr/bin/env python3
"""
receiver.py — Generic microspade real-time telemetry receiver and CSV logger.

This script runs on the PC. It connects to the micro:bit via USB serial,
automatically detects any microspade agent printing its KB, extracts the
dictionary keys dynamically, formats the CLI output, and logs the data
to a local CSV file.

Requirements:
    pip install pyserial
"""

import sys
import os
import time
import re
import ast
import csv
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: The 'pyserial' package is not installed.")
    print("Please install it by running:")
    print("    pip install pyserial")
    print("or if you use uv:")
    print("    uv pip install pyserial")
    sys.exit(1)

# Configuration
BAUD_RATE = 115200
CSV_FILENAME = "sensor_data.csv"
MICROBIT_VID = 0x0D28  # Official micro:bit Vendor ID

# Regex to match agent string: "[agent_name] {key1: val1, key2: val2, ...}"
AGENT_LOG_PATTERN = re.compile(r"^\[([^\]]+)\]\s*(\{.*\})$")


def find_microbit_port():
    """Locate the serial port of the connected micro:bit using its USB Vendor ID."""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if p.vid == MICROBIT_VID or "micro:bit" in (p.description or "").lower():
            return p.device
    return None


def main():
    print("Searching for connected BBC micro:bit...")
    port = find_microbit_port()

    if not port:
        print("Error: No micro:bit detected. Please check your USB connection.")
        sys.exit(1)

    print(f"Found micro:bit on port: {port}")
    print(f"Connecting at {BAUD_RATE} baud...")

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    print("Connected successfully!")
    print(f"Logging data to '{CSV_FILENAME}' (Press Ctrl+C to stop)...")
    print("Waiting for agent telemetry...")

    csv_file = None
    csv_writer = None
    headers = []  # Will be populated dynamically on the first message

    try:
        while True:
            if ser.in_waiting > 0:
                try:
                    line_bytes = ser.readline()
                    line = line_bytes.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue

                # Match the generic agent pattern: [name] {dict}
                match = AGENT_LOG_PATTERN.match(line)
                if match:
                    agent_name = match.group(1)
                    dict_str = match.group(2)
                    
                    try:
                        data = ast.literal_eval(dict_str)
                        if not isinstance(data, dict):
                            continue
                            
                        # Capture timestamp
                        now = datetime.now()
                        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

                        # Initialize CSV headers dynamically on the first valid message
                        if not headers:
                            headers = ["timestamp", "agent_name"] + list(data.keys())
                            file_exists = os.path.exists(CSV_FILENAME)
                            
                            csv_file = open(CSV_FILENAME, "a", newline="", encoding="utf-8")
                            csv_writer = csv.writer(csv_file)
                            
                            if not file_exists:
                                csv_writer.writerow(headers)
                                csv_file.flush()
                            
                            # Print table headers
                            col_widths = [20, 15] + [max(len(k), 10) for k in data.keys()]
                            header_line = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
                            print("\n" + "=" * len(header_line))
                            print(header_line)
                            print("=" * len(header_line))

                        # Format values according to headers
                        row_values = [timestamp_str, agent_name] + [str(data.get(k, "")) for k in headers[2:]]
                        
                        # Print row to CLI
                        col_widths = [20, 15] + [max(len(k), 10) for k in headers[2:]]
                        print(" | ".join(f"{val:<{w}}" for val, w in zip(row_values, col_widths)))
                        
                        # Write to CSV
                        if csv_writer:
                            csv_writer.writerow(row_values)
                            csv_file.flush()

                    except (ValueError, SyntaxError) as parse_error:
                        print(f"[Parse Error] Failed to parse: {line} ({parse_error})")
                elif line:
                    # Print standard non-agent outputs (like setup alerts)
                    print(f"[System Log] {line}")
            
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping telemetry receiver...")
    finally:
        if csv_file:
            csv_file.close()
        ser.close()
        print("Serial connection closed. Goodbye!")


if __name__ == "__main__":
    main()
