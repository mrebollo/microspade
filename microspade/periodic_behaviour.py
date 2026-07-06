from microspade._compat import ticks_ms, ticks_diff
from microspade.behaviour import Behaviour

class PeriodicBehaviour(Behaviour):
    """
    A behaviour that calls :meth:`run` every *period* seconds.

    The first invocation happens immediately on the first scheduler tick.

    Parameters
    ----------
    period:
        Interval in **seconds** (float or int) between successive
        :meth:`run` calls.
    """

    def __init__(self, period):
        super().__init__()
        self._period_ms = int(period * 1000)
        self._last_run = None

    def _step(self):
        now = ticks_ms()
        if (
            self._last_run is None
            or ticks_diff(now, self._last_run) >= self._period_ms
        ):
            self._last_run = now
            self.run()

    def done(self):
        return self._is_done
