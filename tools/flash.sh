#!/usr/bin/env bash
# flash.sh — Flash a Microspade agent to BBC micro:bit V2
#
# Usage:
#   bash tools/flash.sh examples/hello_agent.py
#   bash tools/flash.sh projects/cutebot_controller/
#   bash tools/flash.sh examples/hello_agent.py --firmware   # also flashes MicroPython first
#
# Requirements:
#   - micro:bit V2 connected via USB (appears as /Volumes/MICROBIT)
#   - dist/microspade.py must exist (run tools/build_module.py first)
#   - curl (for --firmware download)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$REPO_ROOT/dist"
MICROSPADE_PY="$DIST_DIR/microspade.py"
MICROBIT_VOLUME="/Volumes/MICROBIT"

FIRMWARE_VERSION="v2.1.1"
FIRMWARE_HEX="$DIST_DIR/micropython-${FIRMWARE_VERSION}.hex"
FIRMWARE_URL="https://github.com/microbit-foundation/micropython-microbit-v2/releases/download/${FIRMWARE_VERSION}/micropython-microbit-${FIRMWARE_VERSION}.hex"

FLASH_FIRMWARE=false
INPUT_PATH=""

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --firmware) FLASH_FIRMWARE=true ;;
        *)          INPUT_PATH="$arg" ;;
    esac
done

if [[ -z "$INPUT_PATH" ]]; then
    echo "Usage: bash tools/flash.sh <directory_or_file> [--firmware]"
    echo ""
    echo "  directory_or_file   Path to a project directory (with main.py) or a .py file"
    echo "  --firmware          Download and flash MicroPython firmware first (only needed once)"
    echo ""
    echo "Examples:"
    echo "  bash tools/flash.sh examples/hello_agent.py"
    echo "  bash tools/flash.sh projects/cutebot_controller/"
    echo "  bash tools/flash.sh examples/hello_agent.py --firmware"
    exit 1
fi

# ---------------------------------------------------------------------------
# Resolve main script and output name
# ---------------------------------------------------------------------------
# Make path absolute if relative
if [[ "$INPUT_PATH" != /* ]]; then
    INPUT_PATH="$REPO_ROOT/$INPUT_PATH"
fi

if [[ -d "$INPUT_PATH" ]]; then
    MAIN_SCRIPT="$INPUT_PATH/main.py"
    OUTPUT_NAME="$(basename "$INPUT_PATH")"
    if [[ ! -f "$MAIN_SCRIPT" ]]; then
        echo "ERROR: main.py not found in: $INPUT_PATH"
        exit 1
    fi
elif [[ -f "$INPUT_PATH" ]]; then
    if [[ "$INPUT_PATH" != *.py ]]; then
        echo "ERROR: Expected a .py file, got: $INPUT_PATH"
        exit 1
    fi
    MAIN_SCRIPT="$INPUT_PATH"
    OUTPUT_NAME="$(basename "$INPUT_PATH" .py)"
else
    echo "ERROR: Path not found: $INPUT_PATH"
    exit 1
fi

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
if [[ ! -f "$MICROSPADE_PY" ]]; then
    echo "ERROR: dist/microspade.py not found. Run first:"
    echo "   uv run tools/build_module.py"
    exit 1
fi

if [[ ! -d "$MICROBIT_VOLUME" ]]; then
    echo "ERROR: micro:bit not found at $MICROBIT_VOLUME"
    echo "   Connect the micro:bit via USB and try again."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 1 (optional): Flash MicroPython firmware
# ---------------------------------------------------------------------------
if [[ "$FLASH_FIRMWARE" == true ]]; then
    echo "Checking MicroPython firmware ${FIRMWARE_VERSION}..."

    if [[ ! -f "$FIRMWARE_HEX" ]]; then
        echo "   Downloading from GitHub..."
        curl -L --progress-bar "$FIRMWARE_URL" -o "$FIRMWARE_HEX"
        echo "   Saved to dist/$(basename "$FIRMWARE_HEX")"
    else
        echo "   Already cached: dist/$(basename "$FIRMWARE_HEX")"
    fi

    echo "Flashing MicroPython firmware..."
    cp "$FIRMWARE_HEX" "$MICROBIT_VOLUME/"
    echo "   Waiting for micro:bit to reboot..."
    sleep 5

    # Wait for volume to remount
    for i in {1..10}; do
        if [[ -d "$MICROBIT_VOLUME" ]]; then
            break
        fi
        sleep 1
    done

    if [[ ! -d "$MICROBIT_VOLUME" ]]; then
        echo "ERROR: micro:bit did not remount after firmware flash."
        echo "   Try again manually once the device is ready."
        exit 1
    fi
    echo "   micro:bit ready."
fi

# ---------------------------------------------------------------------------
# Step 2: Copy microspade.py to micro:bit filesystem
# ---------------------------------------------------------------------------
echo "Copying microspade.py..."
cp "$MICROSPADE_PY" "$MICROBIT_VOLUME/microspade.py"

# ---------------------------------------------------------------------------
# Step 3: Copy main script as main.py
# ---------------------------------------------------------------------------
echo "Copying ${OUTPUT_NAME}.py as main.py..."
cp "$MAIN_SCRIPT" "$MICROBIT_VOLUME/main.py"

echo ""
echo "Done. Files on micro:bit:"
echo "   microspade.py"
echo "   main.py  (from $(basename "$MAIN_SCRIPT"))"
echo ""
echo "Press the reset button on the micro:bit to run."
