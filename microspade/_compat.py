"""
Compatibility shim for MicroPython / CPython time functions.

On micro:bit this module exposes utime helpers directly.
On CPython (e.g. for running tests) it provides equivalent implementations.
"""

try:
    from utime import ticks_ms, ticks_diff, sleep_ms  # MicroPython
except ImportError:
    import time as _time

    def ticks_ms():
        """Return current time in milliseconds (relative, may wrap)."""
        return int(_time.time() * 1000)

    def ticks_diff(new, old):
        """Return signed difference between two ticks values."""
        return new - old

    def sleep_ms(ms):
        """Sleep for *ms* milliseconds."""
        _time.sleep(ms / 1000.0)
