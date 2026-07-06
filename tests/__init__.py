# tests package
import os
import sys

# Add microspade directory to path to enable flat imports during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../microspade")))
import types
import time as _time

# Create and register mock utime module for CPython test environment
utime_mock = types.ModuleType("utime")
utime_mock.ticks_ms = lambda: int(_time.time() * 1000)
utime_mock.ticks_diff = lambda new, old: new - old
utime_mock.sleep_ms = lambda ms: _time.sleep(ms / 1000.0)

sys.modules["utime"] = utime_mock
