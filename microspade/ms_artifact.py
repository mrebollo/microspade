# microbit-module: ms_artifact@0.1.0
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

    def __init__(self, name=None):
        self._observers = []
        self._properties = {}
        self.name = name
        if name is not None:
            from ms_container import container
            container.register_artifact(name, self)

    def add_observer(self, agent):
        """Register an agent to observe this artifact's properties."""
        if agent not in self._observers:
            self._observers.append(agent)
            # Sync existing properties to the agent's KB immediately
            for k, v in self._properties.items():
                agent._receive_property_update(self.name, k, v)

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
                agent._receive_property_update(self.name, name, value)
            # Broadcast over radio for remote observers (if registered)
            if self.name is not None:
                from ms_container import container
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
            body_parts = ["op", self._name, op_name] + [str(arg) for arg in args]
            body = "|".join(body_parts)
            
            from ms_message import Message
            # Broadcast to let any listener board execute the operation
            msg = Message(to="*", sender=self._agent.name, performative="request", body=body)
            self._agent.send(msg)
        return method


# Dynamic Injection (Monkey Patching) to decouple ms_agent from ms_artifact
from ms_agent import Agent

def _agent_on_property_change(self, artifact_name, property_name, value):
    pass

def _agent_receive_property_update(self, artifact_name, property_name, value):
    self.set(property_name, value)
    self.on_property_change(artifact_name, property_name, value)
    handler_name = "on_{}_change".format(property_name)
    handler = getattr(self, handler_name, None)
    if handler is not None:
        handler(value, artifact_name)

def _agent_focus(self, name_or_artifact):
    if not hasattr(self, "_focused_proxies"):
        self._focused_proxies = {}

    from ms_container import container
    if isinstance(name_or_artifact, str):
        name = name_or_artifact
        if name in container.artifacts:
            art = container.artifacts[name]
            art.add_observer(self)
            return art
        else:
            proxy = RemoteArtifactProxy(name, self)
            self._focused_proxies[name] = proxy
            return proxy
    elif isinstance(name_or_artifact, Artifact):
        art = name_or_artifact
        if hasattr(art, "name") and art.name:
            self._focused_proxies[art.name] = art
        art.add_observer(self)
        return art
    else:
        raise TypeError("focus expects a string name or an Artifact instance")

Agent.on_property_change = _agent_on_property_change
Agent._receive_property_update = _agent_receive_property_update
Agent.focus = _agent_focus


from ms_container import AgentContainer

def _container_broadcast_property(self, artifact_name, prop_name, value):
    body = "prop|{}|{}|{}".format(artifact_name, prop_name, str(value))
    from ms_message import Message
    msg = Message(to="*", performative="inform", body=body)
    if self.agents:
        first_agent = next(iter(self.agents.values()))
        first_agent.send(msg)

AgentContainer.broadcast_property = _container_broadcast_property

