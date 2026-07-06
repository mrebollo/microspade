# microspade

**SPADE-like multi-agent framework for the micro:bit platform using MicroPython.**

microspade lets you write intelligent agents with structured *behaviours* and *artifacts* on the [BBC micro:bit](https://microbit.org/), communicating over its built-in 2.4 GHz radio — no XMPP server required. The API is intentionally close to [SPADE](https://github.com/javipalanca/spade) so that programs can be prototyped on a desktop and then deployed to micro:bit with minimal changes.

---

## Features

| Feature | Details |
|---------|---------|
| **Behaviours** | `CyclicBehaviour`, `OneShotBehaviour`, `PeriodicBehaviour`, `TimeoutBehaviour`, `FSMBehaviour` |
| **Artifacts** | Models sensors/actuators with properties synced to agents' KB and callbacks (`on_<prop>_change`) |
| **Message routing** | Template-based routing to individual behaviour mailboxes |
| **Local delivery** | Messages between agents on the **same** board bypass the radio |
| **Radio transport** | Configurable channel, power, queue depth and frame length |
| **Knowledge base** | Per-agent `set(key, value)` / `get(key)` store shared by all behaviours |
| **MicroPython compatible** | Uses only the MicroPython standard library (`utime`, `radio`) |
| **Testable on desktop** | Ships with a `MockTransport` so the full test suite runs on CPython |
| **PC Development Tools** | Minifies, compiles imports, resolves dependencies, and flashes to micro:bit |

---

## Quick start

### 1 — Compile and flash to your micro:bit

You can use the PC-side developer tools to compile, optimize, and upload a script along with its required modular dependencies in a single command.

From the repository root, run:
```bash
# 1. Compile the script and resolve its dependencies
python3 tools/build_module.py examples/hello_agent.py

# 2. Flash it to the connected micro:bit V2 via USB
bash tools/flash.sh
```
*Note: If the board doesn't have MicroPython yet, run `bash tools/flash.sh --firmware` to download and flash it.*

Alternatively, you can manually copy `dist/microspade.py` or the modular `dist/microspade/` directory to the root of your micro:bit's filesystem.

### 2 — Write your first agent

Write your agent script using standard desktop-compatible imports. The build tool will automatically translate these to flat module imports during packaging!

```python
# main.py
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

An `Agent` is the top-level container. Subclass it and override `setup()` to add initial behaviours.

```python
class MyAgent(Agent):
    def setup(self):
        self.add_behaviour(MyBehaviour())
        self.set("counter", 0)   # knowledge-base entry
```

The `run()` method starts the agent and enters the scheduling loop. Use `step()` directly if you need to interleave the scheduler with other code (sensor reads, display updates, etc.).

```python
agent = MyAgent("name")
agent.start()
while True:
    agent.step()
    # ... read sensors, update display ...
```

### Behaviours

Behaviours are the unit of execution. Override `run()` with your logic.

#### `CyclicBehaviour`

`run()` is called on every scheduler tick. The behaviour continues until `kill()` is called.

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

`run()` is called every `period` seconds. The first call happens immediately.

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

Define a finite state machine where each `State` calls `set_next_state()` to transition or `kill()` to end the FSM.

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

### Artifacts

An `Artifact` represents an environmental resource (a physical sensor or actuator, internal or external) that agents can *focus* on. Focusing on an artifact automatically syncs its observable properties to the agent's knowledge base (KB).

When a property changes, the artifact calls `update_property(name, value)`. This notifies all focused agents, updating their KB and triggering an optional `on_<property>_change(value, artifact_name)` callback method on the agent.

#### Define an Artifact

```python
from ms_artifact import Artifact
from microbit import temperature

class TemperatureSensor(Artifact):
    def __init__(self):
        super().__init__()
        self.define_property("temperature", temperature())

    def read_sensor(self):
        self.update_property("temperature", temperature())
```

#### Focus and React

```python
class ThermostatAgent(Agent):
    def __init__(self, name, sensor_artifact):
        super().__init__(name)
        self.sensor = sensor_artifact

    def setup(self):
        self.focus(self.sensor)  # Focuses on the artifact & syncs initial properties

    def on_temperature_change(self, value, artifact_name):
        # Triggered automatically when the physical 'temperature' property changes
        print("Temperature changed to:", value)
```

### Messages

`Message` carries a payload between agents.

| Field | Type | Description |
|-------|------|-------------|
| `to` | `str` or `None` | Recipient name. `None` or `"*"` = broadcast. |
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

Call `receive()` inside `run()`. Pass a `timeout` (seconds) to wait for a message — the scheduler polls the radio during the wait.

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
uv run pytest tests/
```

---

## Project layout

```
microspade/
├── __init__.py        Public API exports (Agent, Artifact, Behaviours, etc.)
├── ms_agent.py        Agent base class and cooperative scheduler
├── ms_artifact.py     Artifact & RemoteArtifactProxy class (for sensors/actuators)
├── ms_behaviour.py    Base Behaviour class
├── ms_container.py    AgentContainer singleton (in-process registry)
├── ms_cyclic.py       CyclicBehaviour class
├── ms_fsm.py          FSMBehaviour & State classes
├── ms_log.py          KB logging utility (log_kb)
├── ms_mailbox.py      Mailbox (FIFO queue for message delivery)
├── ms_message.py      Message & MessageTemplate classes
├── ms_oneshot.py      OneShotBehaviour class
├── ms_periodic.py     PeriodicBehaviour class
├── ms_timeout.py      TimeoutBehaviour class
└── ms_transport.py    RadioTransport class
tests/
├── mocks.py           MockTransport for offline testing
├── test_agent.py      Agent and scheduler tests
├── test_artifact.py   Tests for the new Artifact model
├── test_behaviour.py  Tests for all behaviour types
└── test_message.py    Tests for message encoding/decoding and templates
examples/
├── README.md          Detailed description of all examples
├── hello_agent.py     Simple agent that prints a greeting
├── counter_agent.py   Countdown timer with speech (V2) and rocket animation
├── periodic_agent.py  Toggles corner LED and plays beeps periodically
├── timeout_agent.py   Auto-off timer using TimeoutBehaviour
├── fsm_agent.py       FSM behaviour cycling LED patterns on button presses
├── ping_pong.py       Two boards communicating over the radio
├── artifact_agent.py  Temperature sensor artifact focused by a Thermostat agent
├── rain_sensor_agent.py Interrupt-driven rain warning sensor and reactive callback
├── light_agent.py     Touch logo switch toggling a light artifact with state sync
└── media/             Pre-recorded simulator videos demonstrating the examples
projects/
├── cutebot_controller/ Control agent for the Elecfreaks Cutebot smart car
├── environmental_monitor/ Comfort monitor using temperature, light, and sound (V2)
└── urban_garden/      Smart agriculture automation monitoring system
tools/
├── README.md          Documentation for PC-side helper tools
├── build_module.py    Bundler script (concat/minify/transpile imports/dependencies)
├── flash.sh           Utility to flash modules and main.py to micro:bit V2
└── receiver.py        Generic PC-side USB serial telemetry receiver (auto CSV log)
dist/
├── microspade.py      Bundled single-file minified library (legacy/fallback)
└── microspade/        Directory with individual minified modular files
```

---

## Licence

MIT
