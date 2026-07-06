from microspade._compat import ticks_ms, ticks_diff
from microspade.oneshot_behaviour import OneShotBehaviour

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
        self._triggered = False

    def on_start(self):
        self._trigger_at = ticks_ms() + self._timeout_ms

    def _step(self):
        if self._triggered:
            return
        now = ticks_ms()
        if self._trigger_at is None:
            return
        if ticks_diff(now, self._trigger_at) >= 0:
            self.run()
            self._triggered = True
            self._is_done = True
