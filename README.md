# microspade

**SPADE-like multi-agent framework for the micro:bit platform using MicroPython.**

microspade lets you write intelligent agents with structured *behaviours* on the
[BBC micro:bit](https://microbit.org/), communicating over its built-in 2.4 GHz
radio — no XMPP server required.  The API is intentionally close to
[SPADE](https://github.com/javipalanca/spade) so that programs can be prototyped
on a desktop and then deployed to micro:bit with minimal changes.

---

## Features

| Feature | Details |
|---------|---------|
| **Behaviours** | `CyclicBehaviour`, `OneShotBehaviour`, `PeriodicBehaviour`, `TimeoutBehaviour`, `FSMBehaviour` |
| **Message routing** | Template-based routing to individual behaviour mailboxes |
| **Local delivery** | Messages between agents on the **same** board bypass the radio |
| **Radio transport** | Configurable channel, power, queue depth and frame length |
| **Knowledge base** | Per-agent `set(key, value)` / `get(key)` store shared by all behaviours |
| **MicroPython compatible** | Uses only the MicroPython standard library (`utime`, `radio`) |
| **Testable on desktop** | Ships with a `MockTransport` so the full test suite runs on CPython |

---

## Quick start

### 1 — Copy the library to your micro:bit

Copy the `microspade/` folder to the root of your micro:bit's filesystem.
You can use [uflash](https://uflash.readthedocs.io/),
[mu-editor](https://codewith.mu/), or the
[micro:bit Python editor](https://python.microbit.org/).

### 2 — Write your first agent

```python
# main.py  (flash this to the micro:bit)
from microbit import display
from microspade import Agent, OneShotBehaviour

class GreetBehaviour(OneShotBehaviour):
    def run(self):
        print("Hello, microspade!")
        display.scroll("Hello!")

class HelloAgent(Agent):
    def setup(self):
        self.add_behaviour(GreetBehaviour())

HelloAgent("hello_agent").run()
```

---

## Concepts

### Agent

An `Agent` is the top-level container.  Subclass it and override `setup()` to
add initial behaviours.

```python
class MyAgent(Agent):
    def setup(self):
        self.add_behaviour(MyBehaviour())
        self.set("counter", 0)   # knowledge-base entry
```

The `run()` method starts the agent and enters the scheduling loop.  Use
`step()` directly if you need to interleave the scheduler with other code
(sensor reads, display updates, etc.).

```python
agent = MyAgent("name")
agent.start()
while True:
    agent.step()
    # ... read sensors, update display ...
```

### Behaviours

Behaviours are the unit of execution.  Override `run()` with your logic.

#### `CyclicBehaviour`

`run()` is called on every scheduler tick.  The behaviour continues until
`kill()` is called.

```python
class Counter(CyclicBehaviour):
    def on_start(self):
        self.agent.set("count", 0)

    def run(self):
        n = self.agent.get("count") + 1
        self.agent.set("count", n)
        display.scroll(str(n))
```

#### `OneShotBehaviour`

`run()` is called exactly once, then the behaviour is removed automatically.

```python
class Boot(OneShotBehaviour):
    def run(self):
        display.show(Image.HAPPY)
```

#### `PeriodicBehaviour`

`run()` is called every `period` seconds.  The first call happens immediately.

```python
class Heartbeat(PeriodicBehaviour):
    def run(self):
        display.show(Image.HEART)
        sleep(100)
        display.clear()

agent.add_behaviour(Heartbeat(period=2.0))
```

#### `TimeoutBehaviour`

`run()` is called once after `timeout` seconds have elapsed.

```python
class Alarm(TimeoutBehaviour):
    def run(self):
        display.scroll("Time!")

agent.add_behaviour(Alarm(timeout=5.0))
```

#### `FSMBehaviour` and `State`

Define a finite state machine where each `State` calls `set_next_state()` to
transition or `kill()` to end the FSM.

```python
IDLE, ACTIVE, DONE = "IDLE", "ACTIVE", "DONE"

class IdleState(State):
    def run(self):
        if button_a.was_pressed():
            self.set_next_state(ACTIVE)

class ActiveState(State):
    def run(self):
        if button_b.was_pressed():
            self.set_next_state(DONE)

class DoneState(State):
    def run(self):
        display.show(Image.YES)
        self.kill()   # terminal state

fsm = FSMBehaviour()
fsm.add_state(IDLE, IdleState(), initial=True)
fsm.add_state(ACTIVE, ActiveState())
fsm.add_state(DONE, DoneState())
fsm.add_transition(IDLE, ACTIVE)
fsm.add_transition(ACTIVE, DONE)
agent.add_behaviour(fsm)
```

### Messages

`Message` carries a payload between agents.

| Field | Type | Description |
|-------|------|-------------|
| `to` | `str` or `None` | Recipient name.  `None` or `"*"` = broadcast. |
| `sender` | `str` or `None` | Auto-filled by `send()` when not set. |
| `body` | `str` | Message content. |
| `performative` | `str` | FIPA-style speech act (default `"inform"`). |

```python
msg = Message(to="agent2", body="hello", performative="request")
self.send(msg)

# Reply pattern
reply = msg.make_reply()   # swaps to/sender
reply.body = "acknowledged"
self.send(reply)
```

### MessageTemplate

Templates filter which messages are delivered to a behaviour's mailbox.

```python
# Only "request" messages addressed to this agent
tmpl = MessageTemplate(performative="request")
agent.add_behaviour(MyBehaviour(), template=tmpl)

# Boolean composition
tmpl = MessageTemplate(performative="inform") | MessageTemplate(performative="request")
tmpl = MessageTemplate(sender="coordinator") & MessageTemplate(performative="cfp")
tmpl = ~MessageTemplate(performative="error")   # NOT
```

### Receiving messages

Call `receive()` inside `run()`.  Pass a `timeout` (seconds) to wait for a
message — the scheduler polls the radio during the wait.

```python
class Listener(CyclicBehaviour):
    def run(self):
        msg = self.receive(timeout=0.5)   # wait up to 0.5 s
        if msg:
            display.scroll(msg.body)
```

---

## Radio transport

The default `RadioTransport` wraps the micro:bit `radio` module.

```python
from microspade import Agent, RadioTransport

agent = Agent("my_agent", transport=RadioTransport(
    channel=7,     # 0-83, default 7
    power=6,       # 0-7, default 6
    queue=3,       # receive-queue depth, default 3
    length=32,     # max frame bytes (32 on V1, up to 251 on V2)
))
```

> **Note:** All boards must use the **same channel** to communicate.
> The `length` limit includes the wire-encoded header
> (`TO|FROM|PERFORMATIVE|`), so leave room for the body.
> A 32-byte limit (micro:bit V1) is enough for short messages.

---

## Local routing (same board)

When two agents run in the same MicroPython session, messages are delivered
**directly in memory** via the `container` singleton — no radio hop occurs.
This is useful for running multiple cooperating agents on a single micro:bit.

```python
from microspade import Agent, Message, container

a1 = Agent("alice")
a2 = Agent("bob")
a1.start()
a2.start()

# alice sends to bob — delivered locally, radio not used
msg = Message(to="bob", body="hi")
a1.send(msg)
```

---

## Testing on desktop

The library contains no micro:bit-specific imports at the module level.
Use `MockTransport` from `tests/mocks.py` in your unit tests:

```python
from microspade import Agent, OneShotBehaviour, Message
from tests.mocks import MockTransport

def test_my_behaviour():
    t = MockTransport()
    agent = Agent("test", transport=t)
    agent.start()

    class Ping(OneShotBehaviour):
        def run(self):
            self.send(Message(to="other", body="ping"))

    agent.add_behaviour(Ping())
    agent.step()

    assert "ping" in t._outbox[0]
    agent.stop()
```

Run the bundled test suite:

```bash
pip install pytest
python -m pytest tests/
```

---

## Project layout

```
microspade/
├── __init__.py        Public API
├── _compat.py         MicroPython / CPython time shim
├── message.py         Message, MessageTemplate
├── mailbox.py         Per-behaviour FIFO queue
├── behaviour.py       All behaviour classes + FSM
├── transport.py       RadioTransport
├── container.py       In-process agent registry
└── agent.py           Agent base class + scheduler
tests/
├── mocks.py           MockTransport
├── test_message.py
├── test_behaviour.py
└── test_agent.py
examples/
├── hello_agent.py     Hello-world single agent
├── counter_agent.py   Countdown timer with rocket animation
├── periodic_agent.py  Periodic LED and beep beacon
├── timeout_agent.py   Auto-off timer using TimeoutBehaviour
├── ping_pong.py       Two-board communication
└── fsm_agent.py       Button-driven state machine
tools/
└── build_module.py    Bundler script (removes comments/docstrings)
dist/
├── microspade.py      Bundled single-file module for micro:bit
└── microspade.hex     Optional pre-compiled firmware hex file
```

---

## Licence

MIT
