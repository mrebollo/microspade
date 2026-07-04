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
        self._artifacts = {}

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

    def register_artifact(self, name, artifact):
        """Register *artifact* so it can be focused on locally."""
        self._artifacts[name] = artifact
        artifact.name = name

    def get_artifact(self, name):
        """Return the artifact registered under *name*, or ``None``."""
        return self._artifacts.get(name)

    def has_artifact(self, name):
        """Return ``True`` when an artifact *name* is registered locally."""
        return name in self._artifacts

    def broadcast_property(self, artifact_name, prop_name, value):
        """Broadcast a property update over the radio using the first registered agent."""
        body = "prop|{}|{}|{}".format(artifact_name, prop_name, str(value))
        from microspade.message import Message
        msg = Message(to="*", performative="inform", body=body)
        if self._agents:
            first_agent = next(iter(self._agents.values()))
            first_agent.send(msg)

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
        """Remove all registered agents and artifacts (mainly useful in tests)."""
        self._agents = {}
        self._artifacts = {}


# Module-level convenience alias
container = _AgentContainer.instance()
