# microbit-module: ms_fsm@0.1.0
from ms_behaviour import Behaviour

def _reset_generator(state):
    state._generator = None
    state._yield_deadline = None

class State(Behaviour):
    """
    A single state inside a :class:`FSMBehaviour`.

    Inside :meth:`run`, call :meth:`set_next_state` to request a
    transition.  Call :meth:`kill` (or do neither) to keep looping in
    the same state / terminate the FSM respectively.
    """

    def __init__(self):
        super().__init__()
        self._next_state = None

    def set_next_state(self, state_name):
        """Request a transition to the state named *state_name*."""
        self._next_state = state_name


class FSMBehaviour(Behaviour):
    """
    A Finite State Machine behaviour.

    States are :class:`State` instances registered with :meth:`add_state`.
    Valid transitions between states can optionally be declared with
    :meth:`add_transition`; if no transitions are registered the FSM
    permits any transition.

    Example
    -------
    ::

        class StateA(State):
            def run(self):
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                self.kill()  # terminal – ends the FSM

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())
        agent.add_behaviour(fsm)
    """

    def __init__(self):
        super().__init__()
        self._states = {}
        self._transitions = {}
        self._current_state = None

    # ------------------------------------------------------------------
    # Setup API
    # ------------------------------------------------------------------

    def add_state(self, name, state, initial=False):
        """
        Register a state with the FSM.

        Parameters
        ----------
        name:
            String name for this state.
        state:
            A :class:`State` instance.
        initial:
            If ``True``, this state is the starting point.
        """
        state.set_agent(self.agent)
        self._states[name] = state
        if initial or self._current_state is None:
            self._current_state = name

    def add_transition(self, source, dest):
        """
        Declare a valid transition from *source* to *dest*.

        If no transitions are added to the FSM, all transitions are allowed.
        """
        if source not in self._transitions:
            self._transitions[source] = []
        self._transitions[source].append(dest)

    @property
    def current_state(self):
        """The name of the currently active state."""
        return self._current_state

    # ------------------------------------------------------------------
    # Scheduler interface
    # ------------------------------------------------------------------

    def set_agent(self, agent):
        super().set_agent(agent)
        # Propagate agent link and share FSM mailbox with all states
        for state in self._states.values():
            state.set_agent(agent)
            state._mailbox = self._mailbox

    def _step(self):
        if self._is_done or self._current_state is None:
            self._is_done = True
            return

        state = self._states[self._current_state]

        # Call on_start on the first invocation of this state entry
        if not state._started:
            state.on_start()
            state._started = True

        state._next_state = None
        state._step()

        next_state = state._next_state
        if next_state is not None:
            # Verify and execute transition
            allowed = self._transitions.get(self._current_state)
            if not self._transitions or (allowed and next_state in allowed):
                state.on_end()
                _reset_generator(state)
                state._started = False
                state._is_done = False
                self._current_state = next_state
        elif state.done():
            # State killed itself or generator completed -> FSM terminates
            state.on_end()
            _reset_generator(state)
            self._is_done = True
