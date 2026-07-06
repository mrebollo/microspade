from microspade.behaviour import Behaviour

class CyclicBehaviour(Behaviour):
    """
    A behaviour that runs on every scheduler tick indefinitely.

    It terminates only when :meth:`kill` is called.
    """

    def done(self):
        return self._is_done
