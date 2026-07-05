# Microspade Backlog & Issues Tracking

This file tracks pending bug fixes, improvements, and architectural ideas for the Microspade framework.

---

## 🐛 Open Issues

### 1. Fix Generator Termination Bug in `environmental_monitor`
*   **Severity:** Medium (Silent Failure)
*   **Location:** `projects/environmental_monitor/main.py`
*   **Description:** 
    The behaviors `ComfortIndicator` and `ButtonListener` are implemented as `CyclicBehaviour` classes containing a `yield` statement at the end of their `run()` method, but without a surrounding loop (e.g., `while True:`).
*   **Root Cause:** 
    In Python, a function containing `yield` is a generator. The first scheduling tick executes the behavior up to the `yield` and suspends. The next tick resumes the generator. Since there is no further code after the `yield`, the generator finishes and raises a `StopIteration` exception. The scheduler catches this, marks the behavior as `done`, and deletes it from the agent.
    
    This results in a silent failure: the micro:bit display shows the initial comfort icon forever (giving a false impression of working), but the behaviors are dead and will not update or react to button presses.
*   **Proposed Solution:**
    *   Wrap the execution block inside `run()` in a `while True:` loop to keep the generator alive indefinitely, OR
    *   Refactor the behaviors to inherit from `PeriodicBehaviour` and run their logic periodically without manual generator yields.

---

## 💡 Proposed Features & Enhancements

### 2. Add Conditional Packaging Flags to `build_bundle.py`
*   **Type:** Enhancement / Optimization
*   **Location:** `tools/build_bundle.py`
*   **Description:**
    The BBC micro:bit (especially V1) has extremely strict memory and flash limits. Although the unified Agents & Artifacts (A&A) framework code is small, simple agents that do not use artifacts do not need the artifact-related bytes in the final `microspade.py` bundle.
*   **Proposed Solution:**
    Add conditional command-line arguments to the build tool, for example:
    ```bash
    python tools/build_bundle.py --no-artifacts
    ```
    When this flag is active, the build script should:
    1.  Omit `microspade/artifact.py` from the bundle.
    2.  Strip or mock out the artifact registration and observer syncing logic from `microspade/agent.py` and `microspade/container.py` during compilation.
    This keeps the main git repository unified under a single branch (`main`) while offering maximum byte size flexibility for deployment.

## 🚀 Future Research & Architectural Proposals

### 3. Advanced Agent Architectures: BDI & Brooks Subsumption
*   **Type:** Architectural Extensions & Optimization
*   **Goal:** Provide high-level cognitive (BDI) and low-level reactive (Subsumption) structures optimized for resource-constrained microcontrollers.

#### A. Python-Native BDI (Lite)
Instead of writing a parser for `.asl` logic files, the BDI reasoning cycle is implemented in a native Python Mixin class. Plans are standard Python generator functions (yielding timing delays) associated with a trigger event.
    
*   **Conceptual Implementation Layout (`BDIAgentMixin`):**
    ```python
    class BDIAgentMixin:
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._plans = {}  # Trigger -> Generator function
            self._intentions = []  # List of running plan behaviors
            
        def add_plan(self, trigger, generator_fn):
            """Register a plan. Trigger example: ('+belief', 'raining') or ('+achieve', 'irrigate')"""
            self._plans[trigger] = generator_fn

        def trigger_event(self, event_type, name, value=None):
            """Fires when beliefs change or a goal is added. Instantiates a Plan as a Behaviour."""
            trigger = (event_type, name)
            if trigger in self._plans:
                plan_gen = self._plans[trigger](value)
                
                # Wrap the generator in a OneShotBehaviour to let Microspade schedule it
                from microspade import OneShotBehaviour
                class PlanBehaviour(OneShotBehaviour):
                    def run(self):
                        return plan_gen  # Returns generator to Microspade scheduler
                        
                behaviour = PlanBehaviour()
                self.add_behaviour(behaviour)
                self._intentions.append(behaviour)
    ```
*   **Why it is optimal:** By leveraging Python's native generators, we avoid writing any runtime interpreter logic. Microspade's existing cooperative scheduler becomes the intention execution engine.

#### B. Brooks Subsumption Architecture (Subspade)
Provides reactive layered control (obstacle avoidance, wandering, targeting) where higher priority layers override or inhibit lower layers.
*   **Arbitration:** Behaviors post motor commands to a prioritized channel registry in the agent. The agent's step loop aggregates them and selects the one with the highest priority.
*   **Conceptual Layout (`SubsumptionAgent`):**
    ```python
    class SubsumptionAgent(Agent):
        def __init__(self, name, **kwargs):
            super().__init__(name, **kwargs)
            self._layer_outputs = {}  # Priority (int) -> MotorCommand

        def post_command(self, priority, command):
            self._layer_outputs[priority] = command

        def step(self):
            # 1. Run behaviors (which post commands)
            super().step()
            
            # 2. Arbitrate: Apply highest priority command
            if self._layer_outputs:
                highest_priority = max(self._layer_outputs.keys())
                active_command = self._layer_outputs[highest_priority]
                
                # Apply to actuator artifact
                self.valve.execute_command(active_command)
                
                # Clear outputs for the next tick
                self._layer_outputs.clear()
    ```

#### C. Hybrid BDI-Subsumption Integration
*   **Concept:** Combining BDI cognitive orchestration with low-level Subsumption control.
*   **Optimization Benefit:**
    In resource-constrained microcontrollers, keeping all subsumption layers active in the scheduler is wasteful. For instance, a "Search for Target" behavior does not need to poll sensors or calculate headings if the battery is critical or it is night.
*   **Proposed Integration (Supervised Scheduling):**
    *   **BDI as Supervisor:** The high-level BDI rules evaluate the agent's beliefs (e.g., `battery_low`, `is_night`) and goals.
    *   **Dynamic Scheduling:** Based on rules, BDI dynamically adds or removes active subsumption behaviors from the scheduler agenda.
*   **Conceptual Execution Flow:**
    ```python
    # In the BDIAgentMixin / Supervised Subsumption Agent
    def on_battery_low_change(self, value, artifact_name):
        if value:
            # 1. Remove expensive search behaviors from Microspade scheduler
            self.remove_behaviour(self.search_target_behaviour)
            
            # 2. Add high-priority docking behavior
            self.add_behaviour(self.go_to_dock_behaviour)
            print("BDI Supervisor: Switched to charging state, updated subsumption agenda.")
    ```
*   **Result:** Only relevant behaviors are active, minimizing CPU scheduling overhead while maintaining hierarchical reactive control.
