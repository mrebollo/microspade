"""
AgentContainer — singleton registry for local agent routing.

When an agent sends a message to a name that is registered in the
container the message is delivered directly in memory (no radio hop).
Only messages addressed to unknown agents are forwarded to the transport.

This mirrors SPADE's ``Container`` class.
"""


class _AgentContainer:
    """Singleton container that holds all locally-running agents."""

    _instance = None

    def __init__(self):
        self._agents = {}

    @classmethod
    def instance(cls):
        """Return the single shared container."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, agent):
        """Register *agent* so it can receive messages locally."""
        self._agents[agent.name] = agent

    def unregister(self, agent):
        """Remove *agent* from the registry."""
        self._agents.pop(agent.name, None)

    def has_agent(self, name):
        """Return ``True`` when *name* is registered."""
        return name in self._agents

    def get_agent(self, name):
        """Return the agent registered under *name*, or ``None``."""
        return self._agents.get(name)

    def dispatch(self, msg):
        """
        Route *msg* to the local agent named ``msg.to``.

        Returns ``True`` if the message was delivered locally,
        ``False`` if the destination is unknown (caller should use the
        radio transport instead).
        """
        if msg.to is None:
            return False
        agent = self._agents.get(msg.to)
        if agent is not None:
            agent._dispatch(msg)
            return True
        return False

    def reset(self):
        """Remove all registered agents (mainly useful in tests)."""
        self._agents = {}


# Module-level convenience alias
container = _AgentContainer.instance()
