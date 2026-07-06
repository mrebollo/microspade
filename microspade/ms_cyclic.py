# microbit-module: ms_cyclic@0.1.0
from ms_behaviour import Behaviour

class CyclicBehaviour(Behaviour):
    """
    A behaviour that runs on every scheduler tick indefinitely.

    It terminates only when :meth:`kill` is called.
    """
    pass
