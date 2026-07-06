# microbit-module: ms_container@0.1.0
"""
AgentContainer — singleton registry for local agent routing.

When an agent sends a message to a name that is registered in the
container the message is delivered directly in memory (no radio hop).
Only messages addressed to unknown agents are forwarded to the transport.

This mirrors SPADE's ``Container`` class.
"""


class AgentContainer:
    """Registry that holds all locally-running agents and artifacts."""

    def __init__(self):
        self.agents = {}
        self.artifacts = {}

    def register(self, agent):
        """Register *agent* so it can receive messages locally."""
        self.agents[agent.name] = agent

    def unregister(self, agent):
        """Remove *agent* from the registry."""
        self.agents.pop(agent.name, None)

    def register_artifact(self, name, artifact):
        """Register *artifact* so it can be focused on locally."""
        self.artifacts[name] = artifact
        artifact.name = name
    def dispatch(self, msg):
        """
        Route *msg* to the local agent named ``msg.to``.

        Returns ``True`` if the message was delivered locally,
        ``False`` if the destination is unknown (caller should use the
        radio transport instead).
        """
        if not msg.to:
            return False
        agent = self.agents.get(msg.to)
        if agent:
            agent._dispatch(msg)
            return True
        return False

    def reset(self):
        """Remove all registered agents and artifacts (mainly useful in tests)."""
        self.agents = {}
        self.artifacts = {}


# Module-level convenience alias
container = AgentContainer()
