"""
Artifact support for microspade.

Artifacts represent environmental resources (like sensors or actuators)
that agents can focus on to observe their properties, or interact with
to invoke operations.
"""

class Artifact:
    """
    Base class for all artifacts in the agent's environment.
    """

    def __init__(self):
        self._observers = []
        self._properties = {}
        self.name = None

    def add_observer(self, agent):
        """Register an agent to observe this artifact's properties."""
        if agent not in self._observers:
            self._observers.append(agent)
            # Sync existing properties to the agent's KB immediately
            for k, v in self._properties.items():
                agent.set(k, v)

    def remove_observer(self, agent):
        """Unregister an agent from observing this artifact."""
        if agent in self._observers:
            self._observers.remove(agent)

    def define_property(self, name, value):
        """Define an observable property with an initial value."""
        self._properties[name] = value

    def update_property(self, name, value):
        """Update an observable property and notify all focused agents."""
        if self._properties.get(name) != value:
            self._properties[name] = value
            # Notify local observers
            for agent in self._observers:
                agent.set(name, value)
            # Broadcast over radio for remote observers (if registered)
            if self.name is not None:
                from microspade.container import container
                container.broadcast_property(self.name, name, value)


class RemoteArtifactProxy:
    """
    Proxy that intercepts operation calls on a remote artifact
    and forwards them over the radio transport.
    """

    def __init__(self, name, agent):
        self._name = name
        self._agent = agent

    def __getattr__(self, op_name):
        def method(*args):
            body_parts = ["op", self._name, op_name]
            for arg in args:
                body_parts.append(str(arg))
            body = "|".join(body_parts)
            
            from microspade.message import Message
            # Broadcast to let any listener board execute the operation
            msg = Message(to="*", sender=self._agent.name, performative="request", body=body)
            self._agent.send(msg)
        return method

