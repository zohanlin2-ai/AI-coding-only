# Module M8: Integration & Testing

## Your Task

Responsible for connecting all modules M0–M7, writing a one-click startup script `start.py`, executing end-to-end integration tests, and validating that the entire AI World system operates normally.

---

## Scope of Responsibility

- **Responsible for:**
  - Write `modules/m8_integration/main.py` (`health_check`, `run_integration_tests`, `start_world`, `stop_world`)
  - Write `modules/m8_integration/test_integration.py` (integration test script)
  - Write the root directory `start.py` (one-click system startup)
  - Ensure all modules can be called normally
  - Generate integration test reports

- **Not responsible for:**
  - Any modifications to internal logic of M0–M7
  - Initialization of ChromaDB or SQLite (handled by respective modules)
  - Design of the Streamlit UI (handled by M7)
  - Generation of `config.json` (handled by M0)

---

## Dependencies

- **Prerequisites:** M0, M1, M2, M3, M4, M5, M6, M7 (all)
- **Used by the following modules:** None (M8 is the final integration layer)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m8_integration\
```

---

## Environment Setup

M8 itself has no additional third-party dependencies; all dependencies are installed by M0–M7.  
Confirm that the following packages exist (installed by preceding modules):

```bash
pip install pydantic chromadb ollama streamlit fastapi uvicorn
```

If missing, install:

```bash
pip install requests subprocess32
```

> **Note:** Python's built-in `subprocess` is sufficient; no additional installation is needed.

---

## Files to Create

```
AI_World/
├── start.py                          ← One-click startup script (written by M8 lead)
└── modules/
    └── m8_integration/
        ├── main.py                   ← health_check, run_integration_tests, start_world, stop_world
        └── test_integration.py       ← Integration test script (3 Agents, 5 ticks)
```

---

## Pre-flight Checklist (Must all be checked before integration)

Before writing any M8 code, confirm that each of the following is complete:

### M0 — Setup & Config
- [ ] `config.json` exists in `AI_World/` root directory
- [ ] `config.json` contains fields such as `ollama_model`, `recommended_max_agents`, `tick_interval_sec`, etc.
- [ ] `shared/schemas.py` exists and imports normally

### M1 — World State Engine
- [ ] `modules/m1_world_state/main.py` exists
- [ ] `init_world()`, `get_world_state()`, `add_event()`, `get_tick()`, `save_state()` are all callable
- [ ] `data/world.db` can be created

### M2 — Agent System
- [ ] `modules/m2_agent/main.py` exists
- [ ] `create_agent()`, `agent_act()`, `list_agents()`, `update_agent_needs()` are all callable
- [ ] Ollama service is running (`http://localhost:11434`)

### M3 — Memory System
- [ ] `modules/m3_memory/main.py` exists
- [ ] `save_memory()`, `recall_memory()`, `save_world_event()` are all callable
- [ ] `data/chroma/` directory can be created

### M4 — Multi-Agent Interaction
- [ ] `modules/m4_multi_agent/main.py` exists
- [ ] `run_tick()`, `run_agent_interaction()` are all callable

### M5 — Rules Engine
- [ ] `modules/m5_rules/main.py` exists
- [ ] `get_rules_summary()`, `apply_resource_decay()`, `check_survival()` are all callable

### M6 — Time & History
- [ ] `modules/m6_time_history/main.py` exists
- [ ] `advance_tick()`, `save_snapshot()`, `get_snapshot()` are all callable
- [ ] `data/snapshots/` directory can be created

### M7 — Visualization
- [ ] `modules/m7_visualization/app.py` exists
- [ ] The `streamlit run modules/m7_visualization/app.py` command is executable (not required to be running now)

---

## Shared Schema (Use directly, do not modify)

> Source: `AI_World_Architecture.md`. All modules use the same schema. **Do not create alternative classes yourself.**

```python
# shared/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())[:8]


class Resource(BaseModel):
    food: float = 100.0
    water: float = 100.0
    energy: float = 100.0
    money: float = 100.0
    materials: float = 50.0


class AgentPersonality(BaseModel):
    hunger: float = 0.3      # 0.0~1.0, higher means hungrier
    fear: float = 0.3        # 0.0~1.0, higher means more fearful
    ambition: float = 0.5    # 0.0~1.0, higher means more ambitious
    loyalty: float = 0.5     # 0.0~1.0, higher means more loyal
    aggression: float = 0.3  # 0.0~1.0, higher means more aggressive


class Agent(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    location_id: str
    personality: AgentPersonality = Field(default_factory=AgentPersonality)
    resources: Resource = Field(default_factory=Resource)
    skills: dict[str, float] = Field(default_factory=dict)
    relationships: dict[str, float] = Field(default_factory=dict)
    memory_ids: list[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    is_alive: bool = True
    age: int = 0


class WorldEvent(BaseModel):
    id: str = Field(default_factory=gen_id)
    tick: int
    event_type: str  # "interaction" | "resource" | "conflict" | "discovery" | "death"
    description: str
    affected_agent_ids: list[str] = Field(default_factory=list)
    affected_location_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class WorldState(BaseModel):
    tick: int = 0
    year: int = 1
    season: str = "spring"
    locations: dict[str, Location] = Field(default_factory=dict)
    agents: dict[str, Agent] = Field(default_factory=dict)
    organizations: dict[str, Organization] = Field(default_factory=dict)
    events: list[WorldEvent] = Field(default_factory=list)


class Config(BaseModel):
    ollama_model: str
    ollama_base_url: str = "http://localhost:11434"
    avg_response_time_sec: float
    tokens_per_sec: float
    recommended_max_agents: int
    tick_interval_sec: int
    concurrency_mode: str = "sequential"
    max_concurrent_requests: int = 1
```

**Import Method (Add to the top of all files in M8):**

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.schemas import Config, Agent, AgentPersonality, WorldState, WorldEvent, Resource
```

---

## Provided Functions (Signatures cannot be modified)

```python
# modules/m8_integration/main.py

def health_check() -> dict:
    """
    Check whether all modules (M1–M7) and Ollama service are running normally.
    Returns a dictionary of status for each module, with each value being "ok" or "error".
    """

def run_integration_tests() -> dict:
    """
    Execute end-to-end integration tests (3 Agents, 5 ticks).
    Returns integration test results summary.
    """

def start_world() -> None:
    """
    Start all modules in the correct order (M1→M5→M3→M2→M4→M6→M7).
    """

def stop_world() -> None:
    """
    Safely shut down all modules, stopping the background Streamlit process.
    """
```

### `health_check()` Return Format

```python
{
    "m1_world_state": "ok" | "error",
    "m2_agent": "ok" | "error",
    "m3_memory": "ok" | "error",
    "m4_multi_agent": "ok" | "error",
    "m5_rules": "ok" | "error",
    "m6_time_history": "ok" | "error",
    "m7_visualization": "ok" | "error",
    "ollama": "ok" | "error"
}
```

### `run_integration_tests()` Return Format

```python
{
    "total_ticks": 5,
    "total_events": int,        # Total events accumulated over all ticks
    "agents_alive": int,        # Number of alive Agents at the end of the test
    "memories_saved": int,      # Number of memories successfully written to ChromaDB
    "snapshots_saved": int,     # Number of snapshots successfully saved
    "passed": bool,             # True = all validations passed
    "errors": list[str]         # Error message list of failed items (empty [] when passed)
}
```

---

## External Functions You Can Call

Below are the functions in other modules that M8 needs to call during integration:

### M1 — World State Engine
```python
from modules.m1_world_state.main import (
    init_world,           # (locations: list[Location], config: Config) -> WorldState
    get_world_state,      # () -> WorldState
    update_agent,         # (agent: Agent) -> None
    add_event,            # (event: WorldEvent) -> None
    get_tick,             # () -> int
    save_state,           # () -> None
)
```

### M2 — Agent System
```python
from modules.m2_agent.main import (
    create_agent,         # (name: str, location_id: str, personality: AgentPersonality) -> Agent
    agent_act,            # (agent_id: str) -> WorldEvent
    list_agents,          # () -> list[Agent]
    update_agent_needs,   # (agent_id: str) -> None
)
```

### M3 — Memory System
```python
from modules.m3_memory.main import (
    save_memory,          # (agent_id: str, event: str, importance: float) -> str
    recall_memory,        # (agent_id: str, query: str, top_k: int = 5) -> list[str]
    save_world_event,     # (event: WorldEvent) -> None
)
```

### M4 — Multi-Agent Interaction
```python
from modules.m4_multi_agent.main import (
    run_tick,             # () -> list[WorldEvent]
    run_agent_interaction,# (agent_id_1: str, agent_id_2: str) -> WorldEvent
)
```

### M5 — Rules Engine
```python
from modules.m5_rules.main import (
    get_rules_summary,    # () -> dict
    apply_resource_decay, # (world_state: WorldState) -> WorldState
    check_survival,       # (agent: Agent) -> bool
)
```

### M6 — Time & History
```python
from modules.m6_time_history.main import (
    advance_tick,         # () -> int
    save_snapshot,        # () -> None
    get_snapshot,         # (tick: int) -> Optional[WorldState]
    get_history,          # (start_tick: int, end_tick: int) -> list[WorldEvent]
)
```

---

## Implementation Steps

### Step 1: Create Directory Structure

Confirm that the following directories exist (create them if they do not exist):

```
AI_World/modules/m8_integration/
AI_World/data/snapshots/
```

```python
# Add this helper function at the top of main.py
import os

def _ensure_dirs():
    """Ensure required directories exist"""
    dirs = [
        "data/snapshots",
        "data/chroma",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
```

---

### Step 2: Implement `health_check()`

Logic: Call a lightweight function for each module. If successful, return `"ok"`; on exception, return `"error"`.  
For Ollama, use `requests.get` to call `http://localhost:11434`.

```python
# modules/m8_integration/main.py

import sys, os, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.schemas import Config, Agent, AgentPersonality, WorldEvent

# ---- Load config ----
def _load_config() -> Config:
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return Config(**json.load(f))


def health_check() -> dict:
    """
    Call the lightest function of each module; mark as error if Exception is caught.
    Return format: {"m1_world_state": "ok"|"error", ..., "ollama": "ok"|"error"}
    """
    result = {}

    # --- M1: Call get_tick() ---
    try:
        from modules.m1_world_state.main import get_tick
        get_tick()
        result["m1_world_state"] = "ok"
    except Exception as e:
        result["m1_world_state"] = "error"
        # Optional: print(f"M1 error: {e}")

    # --- M2: Call list_agents() ---
    try:
        # TODO: Implement
        result["m2_agent"] = "ok"
    except Exception:
        result["m2_agent"] = "error"

    # --- M3: Call get_recent_memory (any agent_id, allowing empty result) ---
    try:
        # TODO: Implement
        result["m3_memory"] = "ok"
    except Exception:
        result["m3_memory"] = "error"

    # --- M4: Call get_nearby_agents (allowing empty result) ---
    try:
        # TODO: Implement
        result["m4_multi_agent"] = "ok"
    except Exception:
        result["m4_multi_agent"] = "error"

    # --- M5: Call get_rules_summary() ---
    try:
        from modules.m5_rules.main import get_rules_summary
        summary = get_rules_summary()
        assert isinstance(summary, dict)
        result["m5_rules"] = "ok"
    except Exception:
        result["m5_rules"] = "error"

    # --- M6: Call get_current_season() ---
    try:
        # TODO: Implement
        result["m6_time_history"] = "ok"
    except Exception:
        result["m6_time_history"] = "error"

    # --- M7: Verify app.py file exists ---
    try:
        app_path = os.path.join(
            os.path.dirname(__file__), '..', 'm7_visualization', 'app.py'
        )
        assert os.path.exists(app_path), "app.py not found"
        result["m7_visualization"] = "ok"
    except Exception:
        result["m7_visualization"] = "error"

    # --- Ollama: HTTP GET ---
    try:
        config = _load_config()
        resp = requests.get(config.ollama_base_url, timeout=3)
        result["ollama"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        result["ollama"] = "error"

    return result
```

---

### Step 3: Implement `run_integration_tests()`

Integration test scenario:
- Create 3 Agents with different personalities (A/B/C)
- Execute 5 ticks, calling `run_tick()` each tick
- After each tick, call `advance_tick()` and `save_snapshot()`
- Call `save_memory()` for each Agent
- Finally validate 4 conditions

```python
def run_integration_tests() -> dict:
    """
    Execute 3 Agent x 5 tick integration tests.
    Note: This function modifies the world state. Please run in a clean environment.
    """
    errors = []
    total_events = 0
    memories_saved = 0
    snapshots_saved = 0

    try:
        config = _load_config()

        # ── Step 1: Initialize World ──────────────────────────────
        from modules.m1_world_state.main import init_world, get_world_state, get_tick
        from shared.schemas import Location, Resource

        # Create test locations (at least 1)
        locations = [
            Location(name="TestPlain", x=0, y=0, terrain="plains"),
        ]
        world = init_world(locations, config)
        location_id = list(world.locations.keys())[0]

        # ── Step 2: Create 3 Agents ────────────────────────
        from modules.m2_agent.main import create_agent, list_agents, update_agent_needs

        agent_a = create_agent(
            name="AgentA",
            location_id=location_id,
            personality=AgentPersonality(ambition=0.8),   # High ambition
        )
        agent_b = create_agent(
            name="AgentB",
            location_id=location_id,
            personality=AgentPersonality(aggression=0.7), # High aggression
        )
        agent_c = create_agent(
            name="AgentC",
            location_id=location_id,
            personality=AgentPersonality(loyalty=0.9),    # High loyalty
        )

        # Record initial food/water values for later validation
        initial_resources = {
            agent_a.id: (agent_a.resources.food, agent_a.resources.water),
            agent_b.id: (agent_b.resources.food, agent_b.resources.water),
            agent_c.id: (agent_c.resources.food, agent_c.resources.water),
        }

        # ── Step 3: Execute 5 ticks ─────────────────────────
        from modules.m4_multi_agent.main import run_tick
        from modules.m6_time_history.main import advance_tick, save_snapshot
        from modules.m3_memory.main import save_memory, save_world_event

        for tick_num in range(1, 6):
            # Execute tick (all Agents act)
            events = run_tick()
            total_events += len(events)

            # Save events to Memory
            for event in events:
                try:
                    save_world_event(event)
                except Exception as e:
                    errors.append(f"tick {tick_num} save_world_event failed: {e}")

            # Save this tick's memory for each Agent
            for agent in [agent_a, agent_b, agent_c]:
                try:
                    mem_id = save_memory(
                        agent_id=agent.id,
                        event=f"tick {tick_num} completed, with {len(events)} events",
                        importance=0.5,
                    )
                    if mem_id:
                        memories_saved += 1
                except Exception as e:
                    errors.append(f"tick {tick_num} save_memory({agent.name}) failed: {e}")

            # Update Agent needs
            for agent in [agent_a, agent_b, agent_c]:
                try:
                    update_agent_needs(agent.id)
                except Exception as e:
                    errors.append(f"tick {tick_num} update_agent_needs({agent.name}) failed: {e}")

            # Advance time and save snapshot
            advance_tick()
            try:
                save_snapshot()
                snapshots_saved += 1
            except Exception as e:
                errors.append(f"tick {tick_num} save_snapshot failed: {e}")

        # ── Step 4: Validate Results ───────────────────────────────
        # Validation 1: At least 1 WorldEvent each tick (total 5 ticks, at least 5 events)
        if total_events < 5:
            errors.append(
                f"Validation failed: total_events={total_events}, expected >= 5"
            )

        # Validation 2: Agent food/water lower than initial values
        world_final = get_world_state()
        for agent_id, (init_food, init_water) in initial_resources.items():
            agent_final = world_final.agents.get(agent_id)
            if agent_final is None:
                errors.append(f"Validation failed: agent {agent_id} does not exist in final world state")
                continue
            # TODO: Compare food/water; append error if not decreased
            # if agent_final.resources.food >= init_food:
            #     errors.append(f"Validation failed: {agent_id} food did not decrease")
            # if agent_final.resources.water >= init_water:
            #     errors.append(f"Validation failed: {agent_id} water did not decrease")

        # Validation 3: Memory has been written
        if memories_saved == 0:
            errors.append("Validation failed: memories_saved = 0, ChromaDB did not write any memories")

        # Validation 4: Snapshot exists
        if snapshots_saved == 0:
            errors.append("Validation failed: snapshots_saved = 0, no snapshots saved")

        agents_alive = sum(
            1 for a in world_final.agents.values() if a.is_alive
        )

    except Exception as e:
        errors.append(f"Integration test encountered a critical error: {e}")
        agents_alive = 0

    return {
        "total_ticks": 5,
        "total_events": total_events,
        "agents_alive": agents_alive,
        "memories_saved": memories_saved,
        "snapshots_saved": snapshots_saved,
        "passed": len(errors) == 0,
        "errors": errors,
    }
```

---

### Step 4: Implement `start_world()` and `stop_world()`

```python
import subprocess

# Global variable: store Streamlit process
_streamlit_process = None


def start_world() -> None:
    """
    Start the entire AI World in the correct order.
    Startup sequence: M1 → M5 → M3 → M2 (create Agents) → M4 → M6 → M7 (background)
    """
    global _streamlit_process

    print("=== AI World Starting ===")
    config = _load_config()

    # Step 1: M1 initialize world
    print("[1/7] M1: Initializing world state...")
    from modules.m1_world_state.main import init_world
    from shared.schemas import Location
    # TODO: Create initial location list (recommend at least 4 different terrains)
    locations = [
        Location(name="Northern Plains", x=0, y=0, terrain="plains"),
        Location(name="Eastern Mountain", x=1, y=0, terrain="mountain"),
        Location(name="Southern Forest", x=0, y=1, terrain="forest"),
        Location(name="Western Lake", x=1, y=1, terrain="water"),
    ]
    world = init_world(locations, config)
    print(f"    World initialization complete, locations={len(world.locations)}")

    # Step 2: M5 confirm rules engine
    print("[2/7] M5: Loading rules engine...")
    from modules.m5_rules.main import get_rules_summary
    rules = get_rules_summary()
    print(f"    Rules loaded, rule count={len(rules)}")

    # Step 3: M3 confirm memory system
    print("[3/7] M3: Starting memory system...")
    from modules.m3_memory.main import save_memory
    # Confirm ChromaDB works using a test memory
    # TODO: Call save_memory("__test__", "System Startup", 0.1)
    print("    Memory system normal")

    # Step 4: M2 create initial Agents
    print(f"[4/7] M2: Creating {config.recommended_max_agents} initial Agents...")
    from modules.m2_agent.main import create_agent
    location_ids = list(world.locations.keys())
    for i in range(config.recommended_max_agents):
        # TODO: Create Agent with name f"Agent_{i+1:02d}", randomly assign location
        # Recommend using random.choice(location_ids) to assign location
        pass
    print(f"    {config.recommended_max_agents} Agents created")

    # Step 5: M4 confirm multi-agent interaction mechanism
    print("[5/7] M4: Confirming multi-agent interaction...")
    # M4 itself is stateless, just verify import succeeded
    from modules.m4_multi_agent.main import run_tick
    print("    M4 ready")

    # Step 6: M6 start time management
    print("[6/7] M6: Starting time management...")
    from modules.m6_time_history.main import advance_tick, get_current_season
    season = get_current_season()
    print(f"    Current Season: {season}")

    # Step 7: M7 start Streamlit in background with subprocess
    print("[7/7] M7: Starting Streamlit visualization in background...")
    app_path = os.path.join(
        os.path.dirname(__file__), '..', 'm7_visualization', 'app.py'
    )
    # TODO: Use subprocess.Popen to start streamlit, saving to _streamlit_process
    # _streamlit_process = subprocess.Popen(
    #     ["streamlit", "run", app_path, "--server.headless", "true"],
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.DEVNULL,
    # )
    print(f"    Streamlit started in background (PID: {_streamlit_process.pid if _streamlit_process else 'N/A'})")
    print("    Browser open: http://localhost:8501")

    print("\n=== AI World Started ✓ ===\n")


def stop_world() -> None:
    """
    Safely shut down AI World.
    - Save current world state
    - Terminate background Streamlit process
    """
    global _streamlit_process

    print("=== AI World Shutting Down ===")

    # Save world state
    try:
        from modules.m1_world_state.main import save_state
        save_state()
        print("    World state saved")
    except Exception as e:
        print(f"    Warning: Saving world state failed - {e}")

    # Save final snapshot
    try:
        from modules.m6_time_history.main import save_snapshot
        save_snapshot()
        print("    Final snapshot saved")
    except Exception as e:
        print(f"    Warning: Saving snapshot failed - {e}")

    # Terminate Streamlit
    if _streamlit_process is not None:
        _streamlit_process.terminate()
        _streamlit_process = None
        print("    Streamlit shut down")

    print("=== AI World Safely Shut Down ===")
```

---

### Step 5: Write `test_integration.py`

This script can be executed independently (`python test_integration.py`), and will print a complete test report.

```python
# modules/m8_integration/test_integration.py

import sys
import os
import json
from datetime import datetime

# Path settings: up two levels from m8_integration/ to AI_World/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # Ensure relative paths (data/, config.json) are correct

from modules.m8_integration.main import health_check, run_integration_tests


def print_separator(char="─", width=60):
    print(char * width)


def run_health_check_report():
    """Execute health_check and print formatted report"""
    print_separator("═")
    print("  AI World Health Check")
    print(f"  Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("═")

    results = health_check()

    all_ok = True
    for module, status in results.items():
        icon = "✓" if status == "ok" else "✗"
        print(f"  {icon}  {module:<25} {status}")
        if status != "ok":
            all_ok = False

    print_separator()
    print(f"  Overall Status: {'All normal ✓' if all_ok else 'Some modules abnormal ✗'}")
    print_separator("═")
    return all_ok


def run_integration_test_report():
    """Execute integration tests and print formatted report"""
    print_separator("═")
    print("  AI World Integration Test (3 Agent x 5 Tick)")
    print(f"  Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("═")

    print("  Executing integration tests, please wait...\n")
    results = run_integration_tests()

    print(f"  Total Ticks    : {results['total_ticks']}")
    print(f"  Total Events   : {results['total_events']}")
    print(f"  Agents Alive   : {results['agents_alive']}")
    print(f"  Memories Saved : {results['memories_saved']}")
    print(f"  Snapshots Saved: {results['snapshots_saved']}")
    print_separator()

    if results["passed"]:
        print("  Result: All integration tests passed ✓")
    else:
        print("  Result: Integration test failed ✗")
        print("  Error List:")
        for err in results["errors"]:
            print(f"    - {err}")

    print_separator("═")
    return results["passed"]


def save_report(health_ok: bool, test_results: dict):
    """Save test report as JSON file"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "health_check_passed": health_ok,
        "integration_test": test_results,
    }
    report_path = os.path.join(ROOT, "data", "integration_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Report saved to: {report_path}")


if __name__ == "__main__":
    # Run health check
    health_ok = run_health_check_report()

    if not health_ok:
        print("\n  Some modules failed the health check. Please fix them before running integration tests.")
        sys.exit(1)

    print()

    # Run integration tests
    test_results = run_integration_tests()
    test_ok = run_integration_test_report()

    # Save report
    save_report(health_ok, test_results)

    sys.exit(0 if (health_ok and test_ok) else 1)
```

---

### Step 6: Write Root Directory `start.py`

This is the one-click startup script for the entire system. Users can run `python start.py` to start the AI World and enter interactive mode.

```python
# AI_World/start.py
"""
AI World One-click Startup Script
Execution method: python start.py
"""

import sys
import os
import time
import signal

# Ensure executed in AI_World/ root directory
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def check_config():
    """Confirm config.json exists"""
    config_path = os.path.join(ROOT, "config.json")
    if not os.path.exists(config_path):
        print("✗ config.json not found!")
        print("  Please run M0 setup first:")
        print("  python modules/m0_setup/main.py")
        sys.exit(1)
    print("✓ config.json exists")


def run_health_check():
    """Run health check, warn if any module is abnormal"""
    from modules.m8_integration.main import health_check
    results = health_check()
    failed = [k for k, v in results.items() if v != "ok"]
    if failed:
        print(f"⚠ The following modules failed the health check: {failed}")
        ans = input("   Do you still want to continue booting? [y/N] ").strip().lower()
        if ans != "y":
            print("   Startup cancelled.")
            sys.exit(1)
    else:
        print("✓ All modules passed health check")


def graceful_shutdown(signum, frame):
    """Safely close when Ctrl+C is received"""
    print("\n\nShutdown signal received, safely closing AI World...")
    try:
        from modules.m8_integration.main import stop_world
        stop_world()
    except Exception as e:
        print(f"Warning: Error during shutdown - {e}")
    sys.exit(0)


def main():
    print("╔══════════════════════════════════════╗")
    print("║       AI World — System Startup      ║")
    print("╚══════════════════════════════════════╝\n")

    # 1. Confirm config.json
    check_config()

    # 2. Health check
    print("\n[Pre-flight] Performing module health checks...")
    run_health_check()

    # 3. Start world
    print("\n[Startup] Starting initialization of AI World...\n")
    from modules.m8_integration.main import start_world, stop_world
    signal.signal(signal.SIGINT, graceful_shutdown)

    start_world()

    # 4. Enter tick loop
    print("AI World is running. Press Ctrl+C to safely shut down.\n")
    print("Streamlit visualization interface: http://localhost:8501\n")

    from modules.m4_multi_agent.main import run_tick
    from modules.m6_time_history.main import advance_tick, save_snapshot
    from shared.schemas import Config
    import json

    with open(os.path.join(ROOT, "config.json"), "r") as f:
        config = Config(**json.load(f))

    tick_count = 0
    while True:
        tick_count += 1
        print(f"─── Tick {tick_count} ───────────────────────")

        # Execute tick
        try:
            events = run_tick()
            print(f"    This tick occurred {len(events)} events")
        except Exception as e:
            print(f"    ✗ run_tick failed: {e}")

        # Advance time
        try:
            new_tick = advance_tick()
            print(f"    Time advanced to tick {new_tick}")
        except Exception as e:
            print(f"    ✗ advance_tick failed: {e}")

        # Save snapshot every 10 ticks
        if tick_count % 10 == 0:
            try:
                save_snapshot()
                print(f"    Snapshot saved (tick {tick_count})")
            except Exception as e:
                print(f"    ✗ save_snapshot failed: {e}")

        # Wait for next tick
        time.sleep(config.tick_interval_sec)


if __name__ == "__main__":
    main()
```

---

## Verification Standards (Must pass all to be considered complete)

### Basic Environment
- [ ] `config.json` exists in `AI_World/` root directory, and complies with `Config` schema
- [ ] `shared/schemas.py` imports normally via `from shared.schemas import *`

### Module Health Check
- [ ] `health_check()` runs without throwing exceptions
- [ ] `health_check()` returns `"ok"` for all modules (including `"ollama": "ok"`)

### Integration Testing
- [ ] `run_integration_tests()` runs without throwing exceptions
- [ ] `run_integration_tests()` returns `passed = True`
- [ ] `total_events >= 5` (5 ticks, at least 1 WorldEvent per tick)
- [ ] `food` / `water` of all alive Agents are lower than initial values (100.0)
- [ ] `memories_saved >= 1` (ChromaDB has at least 1 memory written)
- [ ] `snapshots_saved >= 1` (`data/snapshots/` contains snapshot files)

### Data Verification
- [ ] `data/world.db` exists and has data
- [ ] `data/chroma/` exists and has data
- [ ] `data/snapshots/` exists and has at least 1 snapshot file
- [ ] `data/integration_report.json` exists (generated after running `test_integration.py`)

### Startup Script
- [ ] `start.py` exists in the `AI_World/` root directory
- [ ] `python start.py` runs successfully without throwing `ImportError` or `FileNotFoundError`
- [ ] Streamlit interface opens normally at `http://localhost:8501`

### Independent Test Script
- [ ] `python modules/m8_integration/test_integration.py` can be executed independently
- [ ] Output shows `Result: All integration tests passed ✓`

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'shared'`
Verify if the working directory when running the script is `AI_World/`, or add to the top of the script:
```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
```

### `health_check()` returns `"ollama": "error"`
Verify Ollama service is running:
```bash
ollama serve
```
Then confirm `http://localhost:11434` is accessible.

### `run_integration_tests()` returns `memories_saved = 0`
ChromaDB might not be initialized properly. Confirm M3's `save_memory()` can be called normally independently:
```python
from modules.m3_memory.main import save_memory
mem_id = save_memory("test_agent", "Test Memory", 0.5)
print(mem_id)  # Should print memory ID
```

### Streamlit not starting
Verify that M7's `app.py` path is correct and test manually:
```bash
streamlit run modules/m7_visualization/app.py
```

### `total_events < 5`
Verify that M4's `run_tick()` correctly returns a `list[WorldEvent]`, and the list is not empty. Test independently:
```python
from modules.m4_multi_agent.main import run_tick
events = run_tick()
print(f"Events this tick: {len(events)}")
```

---

## Reference: Complete Startup Flowchart

```
python start.py
    │
    ├─ check_config()
    │   └─ config.json ✓
    │
    ├─ health_check() (All modules "ok")
    │
    └─ start_world()
        ├─ [1] M1: init_world()        → data/world.db
        ├─ [2] M5: get_rules_summary() → Confirm rules
        ├─ [3] M3: save_memory(test)   → Confirm ChromaDB
        ├─ [4] M2: create_agent() x N  → Create N Agents
        ├─ [5] M4: run_tick (ready)
        ├─ [6] M6: get_current_season()
        └─ [7] M7: subprocess streamlit → http://localhost:8501
            │
            └─ Enter tick loop
                ├─ run_tick()
                ├─ advance_tick()
                └─ save_snapshot() (every 10 ticks)
```

---

*Last Updated: 2026-05-25 | Corresponding Architecture.md version: 2026-05-25*
