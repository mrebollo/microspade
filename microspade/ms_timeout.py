# microbit-module: ms_timeout@0.1.0
from utime import ticks_ms, ticks_diff
from ms_oneshot import OneShotBehaviour

class TimeoutBehaviour(OneShotBehaviour):
    """
    A behaviour that runs exactly once after *timeout* seconds have elapsed.

    Parameters
    ----------
    timeout:
        Delay in **seconds** before :meth:`run` is called.
    """

    def __init__(self, timeout):
        super().__init__()
        self._timeout_ms = int(timeout * 1000)
        self._trigger_at = None

    def on_start(self):
        self._trigger_at = ticks_ms() + self._timeout_ms

    def _step(self):
        if self._trigger_at is not None and ticks_diff(ticks_ms(), self._trigger_at) >= 0:
            self.run()
            self._trigger_at = None
            self._is_done = True
