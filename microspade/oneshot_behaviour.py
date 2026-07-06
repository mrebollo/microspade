from microspade.behaviour import Behaviour

class OneShotBehaviour(Behaviour):
    """
    A behaviour that runs exactly once and then terminates automatically.
    """

    def _step(self):
        self.run()
        self._is_done = True
