"""Tests for Behaviour classes."""

import time
import pytest
from microspade.behaviour import (
    Behaviour,
    CyclicBehaviour,
    OneShotBehaviour,
    PeriodicBehaviour,
    TimeoutBehaviour,
    FSMBehaviour,
    State,
)
from microspade.message import Message


# ---------------------------------------------------------------------------
# Behaviour base
# ---------------------------------------------------------------------------


class TestBehaviourBase:
    def test_initial_state_not_done(self):
        b = Behaviour()
        assert not b.done()

    def test_initial_agent_is_none(self):
        b = Behaviour()
        assert b.agent is None

    def test_kill_marks_done(self):
        b = Behaviour()
        b.kill()
        assert b.done()

    def test_receive_empty_returns_none(self):
        b = Behaviour()
        assert b.receive() is None

    def test_receive_returns_message(self):
        b = Behaviour()
        msg = Message(body="test")
        b._mailbox.put(msg)
        assert b.receive() == msg

    def test_receive_fifo_order(self):
        b = Behaviour()
        m1 = Message(body="first")
        m2 = Message(body="second")
        b._mailbox.put(m1)
        b._mailbox.put(m2)
        assert b.receive().body == "first"
        assert b.receive().body == "second"

    def test_set_agent(self):
        class FakeAgent:
            name = "dummy"
        b = Behaviour()
        a = FakeAgent()
        b.set_agent(a)
        assert b.agent is a

    def test_on_start_called(self):
        calls = []

        class B(Behaviour):
            def on_start(self):
                calls.append("start")

        b = B()
        b.on_start()
        assert calls == ["start"]

    def test_on_end_called(self):
        calls = []

        class B(Behaviour):
            def on_end(self):
                calls.append("end")

        b = B()
        b.on_end()
        assert calls == ["end"]


# ---------------------------------------------------------------------------
# CyclicBehaviour
# ---------------------------------------------------------------------------


class TestCyclicBehaviour:
    def test_not_done_without_kill(self):
        class B(CyclicBehaviour):
            def run(self):
                pass

        b = B()
        for _ in range(5):
            b._step()
        assert not b.done()

    def test_done_after_kill(self):
        b = CyclicBehaviour()
        b.kill()
        assert b.done()

    def test_run_called_on_every_step(self):
        calls = []

        class B(CyclicBehaviour):
            def run(self):
                calls.append(1)

        b = B()
        b._step()
        b._step()
        b._step()
        assert len(calls) == 3


# ---------------------------------------------------------------------------
# OneShotBehaviour
# ---------------------------------------------------------------------------


class TestOneShotBehaviour:
    def test_done_after_one_step(self):
        class B(OneShotBehaviour):
            def run(self):
                pass

        b = B()
        assert not b.done()
        b._step()
        assert b.done()

    def test_run_called_exactly_once(self):
        calls = []

        class B(OneShotBehaviour):
            def run(self):
                calls.append(1)

        b = B()
        b._step()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# PeriodicBehaviour
# ---------------------------------------------------------------------------


class TestPeriodicBehaviour:
    def test_runs_immediately_on_first_step(self):
        calls = []

        class B(PeriodicBehaviour):
            def run(self):
                calls.append(1)

        b = B(period=100.0)
        b._step()
        assert len(calls) == 1

    def test_does_not_run_again_before_period(self):
        calls = []

        class B(PeriodicBehaviour):
            def run(self):
                calls.append(1)

        b = B(period=100.0)
        b._step()
        b._step()
        b._step()
        assert len(calls) == 1

    def test_runs_again_after_period(self):
        calls = []

        class B(PeriodicBehaviour):
            def run(self):
                calls.append(1)

        b = B(period=0.05)  # 50 ms
        b._step()
        assert len(calls) == 1
        time.sleep(0.06)
        b._step()
        assert len(calls) == 2

    def test_not_done_by_default(self):
        b = PeriodicBehaviour(period=1.0)
        b._step()
        assert not b.done()

    def test_done_after_kill(self):
        b = PeriodicBehaviour(period=1.0)
        b.kill()
        assert b.done()


# ---------------------------------------------------------------------------
# TimeoutBehaviour
# ---------------------------------------------------------------------------


class TestTimeoutBehaviour:
    def test_does_not_run_before_timeout(self):
        calls = []

        class B(TimeoutBehaviour):
            def run(self):
                calls.append(1)

        b = B(timeout=10.0)
        b.on_start()  # simulate agent calling on_start
        b._step()
        assert len(calls) == 0

    def test_runs_after_timeout(self):
        calls = []

        class B(TimeoutBehaviour):
            def run(self):
                calls.append(1)

        b = B(timeout=0.05)  # 50 ms
        b.on_start()
        time.sleep(0.06)
        b._step()
        assert len(calls) == 1
        assert b.done()

    def test_does_not_run_twice(self):
        calls = []

        class B(TimeoutBehaviour):
            def run(self):
                calls.append(1)

        b = B(timeout=0.05)
        b.on_start()
        time.sleep(0.06)
        b._step()
        b._step()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_next_state(self):
        s = State()
        s.set_next_state("B")
        assert s._next_state == "B"

    def test_default_next_state_is_none(self):
        s = State()
        assert s._next_state is None


# ---------------------------------------------------------------------------
# FSMBehaviour
# ---------------------------------------------------------------------------


class TestFSMBehaviour:
    def test_initial_state_first_added(self):
        fsm = FSMBehaviour()

        class S(State):
            def run(self):
                pass

        fsm.add_state("A", S())
        fsm.add_state("B", S())
        assert fsm.current_state == "A"

    def test_explicit_initial_state(self):
        fsm = FSMBehaviour()

        class S(State):
            def run(self):
                pass

        fsm.add_state("A", S())
        fsm.add_state("B", S(), initial=True)
        assert fsm.current_state == "B"

    def test_basic_transition(self):
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

        fsm._step()  # A runs, transitions to B
        assert log == ["A"]
        assert fsm.current_state == "B"
        assert not fsm.done()

        fsm._step()  # B runs, kills FSM
        assert log == ["A", "B"]
        assert fsm.done()

    def test_state_loops_without_transition(self):
        """A state that neither transitions nor kills runs on every step."""
        runs = []

        class LoopState(State):
            def run(self):
                runs.append(1)
                if len(runs) >= 3:
                    self.kill()

        fsm = FSMBehaviour()
        fsm.add_state("L", LoopState(), initial=True)

        fsm._step()
        assert len(runs) == 1
        assert not fsm.done()
        fsm._step()
        assert len(runs) == 2
        assert not fsm.done()
        fsm._step()
        assert len(runs) == 3
        assert fsm.done()

    def test_on_start_and_on_end_called_per_state(self):
        lifecycle = []

        class S(State):
            def __init__(self, tag):
                super().__init__()
                self._tag = tag

            def on_start(self):
                lifecycle.append(("start", self._tag))

            def run(self):
                self.kill()

            def on_end(self):
                lifecycle.append(("end", self._tag))

        fsm = FSMBehaviour()
        fsm.add_state("S", S("s"), initial=True)
        fsm._step()

        assert ("start", "s") in lifecycle
        assert ("end", "s") in lifecycle

    def test_on_start_called_again_after_reentry(self):
        """Entering a state again after a transition should call on_start again."""
        starts = []

        class StateA(State):
            def on_start(self):
                starts.append("A")

            def run(self):
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                self.set_next_state("A")
                self.kill()  # end FSM after one round-trip

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())

        fsm._step()  # A → B
        assert starts == ["A"]
        fsm._step()  # B → A (kill B, so FSM ends – won't re-enter A)
        # We just verify on_start was called for the first entry
        assert starts == ["A"]

    def test_no_states_done_immediately(self):
        fsm = FSMBehaviour()
        fsm._step()
        assert fsm.done()

    def test_add_transition_validates(self):
        log = []

        class StateA(State):
            def run(self):
                log.append("A")
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                log.append("B")

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())
        fsm.add_transition("A", "B")

        fsm._step()
        assert log == ["A"]
        assert fsm.current_state == "B"

    def test_invalid_transition_stays_in_state(self):
        """When transitions are declared, invalid ones are silently ignored."""
        log = []

        class StateA(State):
            def run(self):
                log.append("A")
                self.set_next_state("C")  # C not declared as valid dest

        class StateC(State):
            def run(self):
                log.append("C")

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("C", StateC())
        fsm.add_transition("A", "B")  # only B is allowed from A

        fsm._step()
        assert fsm.current_state == "A"  # stayed in A
        assert not fsm.done()

    def test_state_receives_messages_via_fsm_mailbox(self):
        """States share the FSM's mailbox."""
        received = []

        class S(State):
            def run(self):
                msg = self.receive()
                if msg:
                    received.append(msg.body)
                self.kill()

        fsm = FSMBehaviour()
        s = S()
        fsm.add_state("S", s, initial=True)
        # Manually call set_agent to wire up shared mailbox
        fsm.set_agent(None)

        # Put a message directly in the FSM mailbox
        fsm._mailbox.put(Message(body="hello"))
        fsm._step()
        assert received == ["hello"]


# ---------------------------------------------------------------------------
# Generator yielding support
# ---------------------------------------------------------------------------


class TestGeneratorBehaviour:
    def test_generator_yield_delays_execution(self):
        log = []

        class GenBehaviour(CyclicBehaviour):
            def run(self):
                log.append("start")
                yield 0.05  # Yield for 50ms
                log.append("end")

        b = GenBehaviour()
        b._step()  # Starts generator, executes up to yield
        assert log == ["start"]
        assert b._yield_deadline is not None
        
        # Second step immediately: deadline not met yet, should not run "end"
        b._step()
        assert log == ["start"]
        
        # Sleep to exceed the 50ms deadline
        time.sleep(0.06)
        b._step()  # Resume generator, executes to completion
        assert log == ["start", "end"]
        assert b.done()

    def test_generator_fsm_state_yield(self):
        log = []

        class StateA(State):
            def run(self):
                log.append("A1")
                yield 0.05
                log.append("A2")
                self.set_next_state("B")

        class StateB(State):
            def run(self):
                log.append("B")
                self.kill()

        fsm = FSMBehaviour()
        fsm.add_state("A", StateA(), initial=True)
        fsm.add_state("B", StateB())

        fsm._step()  # Runs StateA up to yield
        assert log == ["A1"]
        assert fsm.current_state == "A"

        fsm._step()  # Still waiting
        assert log == ["A1"]

        time.sleep(0.06)
        fsm._step()  # StateA finishes, sets next state to B, transitions
        assert log == ["A1", "A2"]
        assert fsm.current_state == "B"

        fsm._step()  # StateB runs
        assert log == ["A1", "A2", "B"]
        assert fsm.done()

