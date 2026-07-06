# microbit-module: ms_oneshot@0.1.0
from ms_behaviour import Behaviour

class OneShotBehaviour(Behaviour):
    """
    A behaviour that runs exactly once and then terminates automatically.
    """

    def _step(self):
        self.run()
        self._is_done = True
