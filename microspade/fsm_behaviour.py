from microspade.behaviour import Behaviour

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
        state.set_agent(self._agent)
        self._states[name] = state
        if initial:
            self._current_state = name

    def add_transition(self, source, dest):
        """
        Declare a valid transition from *source* to *dest*.

        If no transitions are added to the FSM, all transitions are allowed.
        """
        if source not in self._transitions:
            self._transitions[source] = []
        self._transitions[source].append(dest)

    # ------------------------------------------------------------------
    # Scheduler interface
    # ------------------------------------------------------------------

    def set_agent(self, agent):
        super().set_agent(agent)
        # Propagate agent link to all registered states
        for state in self._states.values():
            state.set_agent(agent)

    def _step(self):
        if self._is_done or self._current_state is None:
            self._is_done = True
            return

        state = self._states[self._current_state]

        # Call on_start on the first invocation of this state
        if not state._started:
            state.on_start()
            state._started = True

        state._step()

        if state.done():
            # Current state terminated. Find the next state.
            next_state = state._next_state
            state.on_end()
            state._reset_generator()
            state._is_done = False
            state._started = False
            state._next_state = None

            # Verify and execute transition
            if next_state is not None:
                allowed = self._transitions.get(self._current_state)
                # If no transitions are declared, allow any transition.
                # Otherwise, check source -> dest is valid.
                if not self._transitions or (allowed and next_state in allowed):
                    self._current_state = next_state
                else:
                    # Invalid transition or none matches
                    self._current_state = None
                    self._is_done = True
            else:
                # Terminal transition (next_state is None)
                self._current_state = None
                self._is_done = True
