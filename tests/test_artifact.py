"""Tests for the Artifact class."""

import pytest
from ms_agent import Agent
from ms_artifact import Artifact

def test_define_and_update_property():
    art = Artifact()
    art.define_property("temperature", 20)
    assert art._properties["temperature"] == 20

    # Updating property changes the internal state
    art.update_property("temperature", 25)
    assert art._properties["temperature"] == 25


def test_agent_focus_syncs_initial_properties():
    class DummyAgent(Agent):
        def setup(self):
            pass

    agent = DummyAgent("dummy")
    art = Artifact()
    art.define_property("temperature", 22)
    art.define_property("humidity", 50)

    # Before focus, agent's KB is empty
    assert agent.get("temperature") is None
    assert agent.get("humidity") is None

    # Focus registers agent and syncs properties
    agent.focus(art)
    assert agent.get("temperature") == 22
    assert agent.get("humidity") == 50


def test_agent_receives_property_updates():
    class DummyAgent(Agent):
        def setup(self):
            pass

    agent = DummyAgent("dummy")
    art = Artifact()
    art.define_property("temperature", 22)
    
    agent.focus(art)
    assert agent.get("temperature") == 22

    # Updating the property updates the agent's KB
    art.update_property("temperature", 26)
    assert agent.get("temperature") == 26


def test_remove_observer_stops_updates():
    class DummyAgent(Agent):
        def setup(self):
            pass

    agent = DummyAgent("dummy")
    art = Artifact()
    art.define_property("temperature", 22)
    
    agent.focus(art)
    art.remove_observer(agent)

    # Updating property after removal should not update agent's KB
    art.update_property("temperature", 30)
    assert agent.get("temperature") == 22  # Remains at old value


def test_container_artifact_registration():
    from ms_container import container
    container.reset()
    
    art = Artifact()
    assert "sensor1" not in container.artifacts
    
    container.register_artifact("sensor1", art)
    assert "sensor1" in container.artifacts
    assert container.artifacts.get("sensor1") is art
    assert art.name == "sensor1"


def test_local_focus_by_name():
    from ms_container import container
    container.reset()

    class DummyAgent(Agent):
        def setup(self):
            pass

    agent = DummyAgent("dummy")
    art = Artifact()
    art.define_property("temperature", 22)
    container.register_artifact("temp_sensor", art)

    # Focus by name should return the real local artifact
    focused = agent.focus("temp_sensor")
    assert focused is art
    assert agent.get("temperature") == 22

    # Updates should propagate
    art.update_property("temperature", 25)
    assert agent.get("temperature") == 25


def test_remote_focus_by_name_creates_proxy():
    from ms_container import container
    from ms_artifact import RemoteArtifactProxy
    container.reset()

    class DummyAgent(Agent):
        def setup(self):
            pass

    agent = DummyAgent("dummy")
    
    # Focusing on a name not in container creates a proxy
    focused = agent.focus("remote_heater")
    assert isinstance(focused, RemoteArtifactProxy)
    assert focused._name == "remote_heater"
    assert focused._agent is agent


def test_remote_operation_routing():
    from tests.mocks import MockTransport
    from ms_message import Message

    class DummyAgent(Agent):
        def setup(self):
            pass

    t = MockTransport()
    agent = DummyAgent("dummy", transport=t)
    agent.start()

    proxy = agent.focus("remote_heater")
    # Invoke an operation on the proxy
    proxy.set_temperature(24, True, "high")

    # The transport should have sent a broadcast message
    assert len(t._outbox) == 1
    msg = Message.decode(t._outbox[0])
    assert msg.to == "*"
    assert msg.sender == "dummy"
    assert msg.performative == "request"
    assert msg.body == "op|remote_heater|set_temperature|24|True|high"


def test_remote_property_update_decoding():
    from tests.mocks import MockTransport
    from ms_message import Message

    class DummyAgent(Agent):
        def setup(self):
            pass

    t = MockTransport()
    agent = DummyAgent("dummy", transport=t)
    agent.start()

    # Focus on remote artifact to register interest
    agent.focus("remote_sensor")

    # Simulate receiving a property update message
    msg = Message(to="*", sender="remote_board", performative="inform", body="prop|remote_sensor|humidity|65")
    t.inject_message(msg)
    agent.step()

    # Agent's KB should be updated automatically
    assert agent.get("humidity") == 65


def test_remote_operation_execution():
    from tests.mocks import MockTransport
    from ms_container import container
    from ms_message import Message
    container.reset()

    class CustomHeater(Artifact):
        def __init__(self):
            super().__init__()
            self.last_temp = None
            self.last_active = None

        def set_state(self, temp, active):
            self.last_temp = temp
            self.last_active = active

    heater = CustomHeater()
    container.register_artifact("livingroom_heater", heater)

    t = MockTransport()
    agent = Agent("host_agent", transport=t)
    agent.start()

    # Simulate receiving a request to run an operation on our artifact
    msg = Message(to="*", sender="remote_agent", performative="request", body="op|livingroom_heater|set_state|22|True")
    t.inject_message(msg)
    agent.step()

    # Local artifact's operation should have been invoked with correct typed args
    assert heater.last_temp == 22
    assert heater.last_active is True


def test_dynamic_property_change_callbacks():
    class CallbackAgent(Agent):
        def __init__(self, name, **kwargs):
            super().__init__(name, **kwargs)
            self.changed_properties = []
            self.temp_changed_to = None
            self.temp_changed_art = None

        def on_property_change(self, artifact_name, property_name, value):
            self.changed_properties.append((artifact_name, property_name, value))

        def on_temperature_change(self, value, artifact_name):
            self.temp_changed_to = value
            self.temp_changed_art = artifact_name

    agent = CallbackAgent("callback_agent")
    art = Artifact("temp_sensor")
    art.define_property("temperature", 22)
    art.define_property("humidity", 50)

    agent.focus(art)

    # Initial sync triggers callbacks
    assert ("temp_sensor", "temperature", 22) in agent.changed_properties
    assert ("temp_sensor", "humidity", 50) in agent.changed_properties
    assert agent.temp_changed_to == 22
    assert agent.temp_changed_art == "temp_sensor"

    # Property update triggers callbacks
    agent.changed_properties.clear()
    agent.temp_changed_to = None
    
    art.update_property("temperature", 25)
    assert ("temp_sensor", "temperature", 25) in agent.changed_properties
    assert agent.temp_changed_to == 25
    assert agent.temp_changed_art == "temp_sensor"


