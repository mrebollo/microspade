"""Tests for Agent and AgentContainer."""

import pytest
from microspade.agent import Agent
from microspade.behaviour import (
    CyclicBehaviour,
    OneShotBehaviour,
    PeriodicBehaviour,
    FSMBehaviour,
    State,
)
from microspade.message import Message, MessageTemplate
from microspade.container import _AgentContainer
from tests.mocks import MockTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_agent(name="test_agent"):
    t = MockTransport()
    a = Agent(name, transport=t)
    a.start()
    return a, t


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------


class TestAgentLifecycle:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.agent, self.transport = make_agent()

    def teardown_method(self):
        if self.agent.is_alive():
            self.agent.stop()
        _AgentContainer.instance().reset()

    def test_start_calls_transport_setup(self):
        assert self.transport._setup_called

    def test_stop_calls_transport_teardown(self):
        self.agent.stop()
        assert self.transport._teardown_called

    def test_is_alive_after_start(self):
        assert self.agent.is_alive()

    def test_not_alive_after_stop(self):
        self.agent.stop()
        assert not self.agent.is_alive()

    def test_setup_hook_called(self):
        setup_calls = []

        class MyAgent(Agent):
            def setup(self):
                setup_calls.append(1)

        _AgentContainer.instance().reset()
        a = MyAgent("a2", transport=MockTransport())
        a.start()
        assert len(setup_calls) == 1
        a.stop()

    def test_setup_hook_can_add_behaviours(self):
        class MyAgent(Agent):
            def setup(self):
                self.add_behaviour(OneShotBehaviour())

        _AgentContainer.instance().reset()
        a = MyAgent("a3", transport=MockTransport())
        a.start()
        assert len(a._behaviours) == 1
        a.stop()


# ---------------------------------------------------------------------------
# Behaviour management
# ---------------------------------------------------------------------------


class TestBehaviourManagement:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.agent, self.transport = make_agent()

    def teardown_method(self):
        if self.agent.is_alive():
            self.agent.stop()
        _AgentContainer.instance().reset()

    def test_add_behaviour(self):
        b = OneShotBehaviour()
        self.agent.add_behaviour(b)
        assert self.agent.has_behaviour(b)

    def test_remove_behaviour(self):
        b = CyclicBehaviour()
        self.agent.add_behaviour(b)
        self.agent.remove_behaviour(b)
        assert not self.agent.has_behaviour(b)

    def test_has_behaviour_false_for_unknown(self):
        b = CyclicBehaviour()
        assert not self.agent.has_behaviour(b)

    def test_behaviour_linked_to_agent(self):
        b = OneShotBehaviour()
        self.agent.add_behaviour(b)
        assert b.agent is self.agent

    def test_oneshot_runs_and_is_removed(self):
        runs = []

        class B(OneShotBehaviour):
            def run(self):
                runs.append(1)

        self.agent.add_behaviour(B())
        self.agent.step()
        assert runs == [1]
        assert len(self.agent._behaviours) == 0

    def test_cyclic_keeps_running(self):
        runs = []

        class B(CyclicBehaviour):
            def run(self):
                runs.append(1)

        self.agent.add_behaviour(B())
        for _ in range(3):
            self.agent.step()
        assert len(runs) == 3
        assert len(self.agent._behaviours) == 1

    def test_on_start_called_before_first_run(self):
        order = []

        class B(OneShotBehaviour):
            def on_start(self):
                order.append("start")

            def run(self):
                order.append("run")

        self.agent.add_behaviour(B())
        self.agent.step()
        assert order == ["start", "run"]

    def test_on_end_called_after_done(self):
        calls = []

        class B(OneShotBehaviour):
            def run(self):
                pass

            def on_end(self):
                calls.append("end")

        self.agent.add_behaviour(B())
        self.agent.step()
        assert "end" in calls

    def test_cyclic_kill_removes_behaviour(self):
        class B(CyclicBehaviour):
            def run(self):
                self.kill()

        self.agent.add_behaviour(B())
        self.agent.step()
        assert len(self.agent._behaviours) == 0


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


class TestAgentMessaging:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.agent, self.transport = make_agent()

    def teardown_method(self):
        if self.agent.is_alive():
            self.agent.stop()
        _AgentContainer.instance().reset()

    def test_send_uses_transport(self):
        msg = Message(to="other", body="hello")
        self.agent.send(msg)
        assert len(self.transport._outbox) == 1

    def test_send_fills_sender(self):
        msg = Message(to="other", body="hello")
        self.agent.send(msg)
        decoded = Message.decode(self.transport._outbox[0])
        assert decoded.sender == "test_agent"

    def test_send_does_not_overwrite_sender(self):
        msg = Message(to="other", sender="already_set", body="hi")
        self.agent.send(msg)
        decoded = Message.decode(self.transport._outbox[0])
        assert decoded.sender == "already_set"

    def test_step_polls_transport(self):
        received = []

        class B(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    received.append(msg.body)

        self.agent.add_behaviour(B())
        incoming = Message(to="test_agent", sender="other", body="ping")
        self.transport.inject_message(incoming)
        self.agent.step()
        assert received == ["ping"]

    def test_message_for_other_agent_ignored(self):
        received = []

        class B(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    received.append(msg)

        self.agent.add_behaviour(B())
        msg = Message(to="other_agent", sender="x", body="private")
        self.transport.inject_message(msg)
        self.agent.step()
        assert received == []

    def test_broadcast_message_delivered(self):
        """Message with to=None is delivered to all behaviours."""
        received = []

        class B(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    received.append(msg.body)

        self.agent.add_behaviour(B())
        msg = Message(to=None, sender="x", body="broadcast")
        self.transport.inject_message(msg)
        self.agent.step()
        assert received == ["broadcast"]

    def test_wildcard_star_delivered(self):
        """Message with to='*' is delivered like a broadcast."""
        received = []

        class B(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    received.append(msg.body)

        self.agent.add_behaviour(B())
        msg = Message(to="*", sender="x", body="all")
        self.transport.inject_message(msg)
        self.agent.step()
        assert received == ["all"]

    def test_template_routes_to_correct_behaviour(self):
        req_msgs = []
        inf_msgs = []

        class ReqBeh(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    req_msgs.append(msg.body)

        class InfBeh(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    inf_msgs.append(msg.body)

        self.agent.add_behaviour(ReqBeh(), template=MessageTemplate(performative="request"))
        self.agent.add_behaviour(InfBeh(), template=MessageTemplate(performative="inform"))

        self.transport.inject_message(
            Message(to="test_agent", sender="x", body="r", performative="request")
        )
        self.agent.step()

        assert req_msgs == ["r"]
        assert inf_msgs == []

    def test_first_matching_template_wins(self):
        """Only the first matching behaviour gets each message."""
        first = []
        second = []

        class First(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    first.append(msg.body)

        class Second(CyclicBehaviour):
            def run(self):
                msg = self.receive()
                if msg:
                    second.append(msg.body)

        self.agent.add_behaviour(First())   # no template → matches all
        self.agent.add_behaviour(Second())  # no template → matches all

        self.transport.inject_message(
            Message(to="test_agent", sender="x", body="once")
        )
        self.agent.step()

        # Message should arrive in exactly one behaviour
        assert first + second == ["once"]
        assert not (first and second)


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------


class TestAgentKnowledgeBase:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.agent, _ = make_agent()

    def teardown_method(self):
        if self.agent.is_alive():
            self.agent.stop()
        _AgentContainer.instance().reset()

    def test_set_and_get(self):
        self.agent.set("counter", 42)
        assert self.agent.get("counter") == 42

    def test_get_missing_returns_none(self):
        assert self.agent.get("missing") is None

    def test_behaviour_can_access_kb(self):
        result = []

        class B(OneShotBehaviour):
            def run(self):
                result.append(self.agent.get("key"))

        self.agent.set("key", "value")
        self.agent.add_behaviour(B())
        self.agent.step()
        assert result == ["value"]


# ---------------------------------------------------------------------------
# Local container routing
# ---------------------------------------------------------------------------


class TestLocalRouting:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.t1 = MockTransport()
        self.t2 = MockTransport()
        self.a1 = Agent("alice", transport=self.t1)
        self.a2 = Agent("bob", transport=self.t2)
        self.a1.start()
        self.a2.start()

    def teardown_method(self):
        if self.a1.is_alive():
            self.a1.stop()
        if self.a2.is_alive():
            self.a2.stop()
        _AgentContainer.instance().reset()

    def test_local_message_does_not_use_transport(self):
        """Messages between registered local agents bypass the radio."""
        msg = Message(to="bob", body="local")
        self.a1.send(msg)
        # Nothing should be in alice's transport outbox
        assert len(self.t1._outbox) == 0

    def test_local_message_delivered_to_destination(self):
        received = []

        class B(CyclicBehaviour):
            def run(self):
                m = self.receive()
                if m:
                    received.append(m.body)

        self.a2.add_behaviour(B())
        msg = Message(to="bob", body="hi")
        self.a1.send(msg)
        self.a2.step()
        assert received == ["hi"]

    def test_unknown_recipient_uses_transport(self):
        msg = Message(to="charlie", body="external")
        self.a1.send(msg)
        assert len(self.t1._outbox) == 1


# ---------------------------------------------------------------------------
# FSM integration
# ---------------------------------------------------------------------------


class TestFSMIntegration:
    def setup_method(self):
        _AgentContainer.instance().reset()
        self.agent, self.transport = make_agent()

    def teardown_method(self):
        if self.agent.is_alive():
            self.agent.stop()
        _AgentContainer.instance().reset()

    def test_fsm_runs_through_states(self):
        log = []

        class StateA(State):
            def run(self):
                log.append("A")
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                log.append("B")
                self.kill()

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())
        self.agent.add_behaviour(fsm)

        self.agent.step()  # A → B
        self.agent.step()  # B → done
        self.agent.step()  # fsm removed

        assert log == ["A", "B"]
        assert len(self.agent._behaviours) == 0
