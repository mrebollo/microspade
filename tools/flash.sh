#!/usr/bin/env bash
# flash.sh — Flash Microspade modular modules and main.py to BBC micro:bit V2
#
# Usage:
#   bash tools/flash.sh [--firmware]
#
# Requirements:
#   - micro:bit V2 connected via USB
#   - dist/microspade/ must exist (run tools/build_module.py first)
#   - mpremote installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$REPO_ROOT/dist"
MICROSPADE_DIST_DIR="$DIST_DIR/microspade"
MICROBIT_VOLUME="/Volumes/NO NAME"

FIRMWARE_VERSION="v2.1.1"
FIRMWARE_HEX="$DIST_DIR/micropython-${FIRMWARE_VERSION}.hex"
FIRMWARE_URL="https://github.com/microbit-foundation/micropython-microbit-v2/releases/download/${FIRMWARE_VERSION}/micropython-microbit-${FIRMWARE_VERSION}.hex"

FLASH_FIRMWARE=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --firmware) FLASH_FIRMWARE=true ;;
        *)
            echo "ERROR: Unknown argument: $arg"
            echo "Usage: bash tools/flash.sh [--firmware]"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
if [[ ! -d "$MICROSPADE_DIST_DIR" ]]; then
    echo "ERROR: dist/microspade/ not found. Run first:"
    echo "   python3 tools/build_module.py"
    exit 1
fi

# Validate mpremote dependency
if command -v mpremote &> /dev/null; then
    MPREMOTE_CMD="mpremote"
elif command -v uv &> /dev/null; then
    MPREMOTE_CMD="uv run mpremote"
else
    echo "ERROR: 'mpremote' command not found."
    echo "   Please install it with: uv pip install mpremote"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 1 (optional): Flash MicroPython firmware via USB Mass Storage
# ---------------------------------------------------------------------------
if [[ "$FLASH_FIRMWARE" == true ]]; then
    if [[ ! -d "$MICROBIT_VOLUME" ]]; then
        # Try default Volume if custom one is not mounted
        if [[ -d "/Volumes/MICROBIT" ]]; then
            MICROBIT_VOLUME="/Volumes/MICROBIT"
        else
            echo "ERROR: micro:bit USB volume not found at $MICROBIT_VOLUME or /Volumes/MICROBIT"
            echo "   Connect the micro:bit via USB and try again."
            exit 1
        fi
    fi

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
# Step 2: Copy flat modules and main.py to micro:bit filesystem in a single session
# ---------------------------------------------------------------------------
CLEANUP_CODE=$(cat << 'EOF'
import os
print("Files on micro:bit before cleanup:", os.listdir())
def rm_rf(p):
    try:
        print("  Deleting:", p)
        if os.stat(p)[0] & 0x4000:
            for f in os.listdir(p):
                rm_rf(p + '/' + f)
            os.rmdir(p)
        else:
            os.remove(p)
    except Exception as e:
        print("  Failed to delete", p, ":", str(e))
for f in os.listdir():
    rm_rf(f)
print("Files on micro:bit after cleanup:", os.listdir())
EOF
)

MPREMOTE_ARGS=("resume")

# Clean up existing files recursively to free up all space
MPREMOTE_ARGS+=("exec" "$CLEANUP_CODE" "+")

if [[ -f "$DIST_DIR/dependencies.txt" ]]; then
    echo "Reading dependencies list..."
    while IFS= read -r filename || [[ -n "$filename" ]]; do
        filename="$(echo "$filename" | xargs)"
        if [[ -n "$filename" ]]; then
            f="$MICROSPADE_DIST_DIR/$filename"
            if [[ -f "$f" ]]; then
                MPREMOTE_ARGS+=("cp" "$f" ":$filename" "+")
            fi
        fi
    done < "$DIST_DIR/dependencies.txt"
else
    echo "Warning: dist/dependencies.txt not found. Copying all modules..."
    for f in "$MICROSPADE_DIST_DIR"/*.py; do
        filename="$(basename "$f")"
        if [[ "$filename" != "__init__.py" ]]; then
            MPREMOTE_ARGS+=("cp" "$f" ":$filename" "+")
        fi
    done
fi

if [[ -f "$DIST_DIR/main.py" ]]; then
    MPREMOTE_ARGS+=("cp" "$DIST_DIR/main.py" ":main.py" "+")
fi

# Remove the trailing "+" if present
last_idx=$(( ${#MPREMOTE_ARGS[@]} - 1 ))
if [[ "$last_idx" -ge 0 && "${MPREMOTE_ARGS[last_idx]}" == "+" ]]; then
    unset "MPREMOTE_ARGS[last_idx]"
fi

MPREMOTE_ARGS+=("+" "ls")

echo "Uploading files to micro:bit in a single serial session..."
$MPREMOTE_CMD "${MPREMOTE_ARGS[@]}"

echo ""
echo "Press the reset button on the micro:bit to run."
