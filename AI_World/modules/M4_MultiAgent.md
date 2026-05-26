# Module M4: Multi-Agent Interaction Engine

## Your Task

Coordinate the interaction of multiple Agents in the same AI World, and drive the complete tick cycle — for each tick, let all alive Agents sequentially complete needs updates, survival checks, proximity interactions, action execution, and memory storage, and finally return all `WorldEvent`s occurring in this tick.

---

## Scope of Responsibility

- **Responsible for:**
  - Implement the complete tick drive process of `run_tick()`
  - Determine which Agents are at the same location (`get_nearby_agents()`)
  - Drive interaction events between two Agents (`run_agent_interaction()`)
  - Drive negotiation process and update Agent relationships (`negotiate()`)
  - Coordinate calls to external functions of M1, M2, M3, M5
  - Ensure deceased Agents do not participate in subsequent ticks

- **Not responsible for:**
  - LLM calls themselves (handled by M2's `agent_think` / `agent_act`)
  - Resource decay rule calculation (handled by M5's `apply_resource_decay`)
  - Action validity verification logic (handled by M5's `validate_action`)
  - Memory vector storage details (handled by M3's `save_memory`)
  - Persistence of the world state (handled by M1's `add_event` / `update_agent`)
  - Time advancement (`advance_tick()` handled by M6)

---

## Dependencies

- **Prerequisites:**
  - M0 (Provides `config.json`)
  - M1 (Provides `get_world_state`, `add_event`, `update_agent`)
  - M2 (Provides `agent_think`, `agent_act`, `update_agent_needs`, `list_agents`)
  - M3 (Provides `save_memory`, `recall_memory`)
  - M5 (Provides `validate_action`, `apply_resource_decay`, `check_survival`)

- **Used by the following modules:**
  - M8 (Calls `run_tick()` during integration testing)
  - M6 (Time system calls M4 to drive the world after each tick)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m4_multi_agent\
```

---

## Environment Setup

```bash
pip install pydantic
```

> [!NOTE]
> `pydantic` is used for Schema validation. M4 itself does not directly install LLM or database packages; all LLM / DB operations are completed by calling functions from M2 and M3.

---

## Files to Create

```
AI_World/
└── modules/
    └── m4_multi_agent/
        └── main.py          ← The only file to implement
```

> [!IMPORTANT]
> **No need** to create `__init__.py`. The entire module has only one `main.py`.

---

## Shared Schema (Use directly, do not modify)

The following Schema is defined in `shared/schemas.py`. M4 **must** use it via `from shared.schemas import *`; redefining these classes is prohibited.

```python
# shared/schemas.py (Excerpt of M4-related parts)

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
    relationships: dict[str, float] = Field(default_factory=dict)  # agent_id -> -1.0~1.0
    memory_ids: list[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    is_alive: bool = True
    age: int = 0  # Unit: tick


class Location(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    x: int
    y: int
    terrain: str  # "plains" | "mountain" | "forest" | "water"
    resources: Resource = Field(default_factory=Resource)


class Organization(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    type: str  # "tribe" | "company" | "nation"
    member_ids: list[str] = Field(default_factory=list)
    leader_id: Optional[str] = None
    resources: Resource = Field(default_factory=Resource)
    territory: list[str] = Field(default_factory=list)


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
    season: str = "spring"  # "spring" | "summer" | "autumn" | "winter"
    locations: dict[str, Location] = Field(default_factory=dict)
    agents: dict[str, Agent] = Field(default_factory=dict)
    organizations: dict[str, Organization] = Field(default_factory=dict)
    events: list[WorldEvent] = Field(default_factory=list)
```

---

## Provided Functions (Signatures cannot be modified)

The following four functions are the **external contract** of M4. Function names, parameter names, parameter types, and return types **must not be changed**.

```python
def run_agent_interaction(agent_id_1: str, agent_id_2: str) -> WorldEvent:
    """Drive two Agents to interact, returning the interaction event"""

def run_tick() -> list[WorldEvent]:
    """Execute a complete tick (all Agents act sequentially), returning all events in this tick"""

def negotiate(agent_id_1: str, agent_id_2: str, topic: str) -> dict:
    """Drive two Agents to negotiate on a topic, returning the result {success: bool, outcome: str}"""

def get_nearby_agents(agent_id: str, radius: int = 1) -> list[Agent]:
    """Return all alive Agents within radius grids of the specified Agent"""
```

---

## External Functions You Can Call

The following are other module functions M4 is allowed to call. Use the full import path when calling, and **do not** bypass these interfaces to operate the database directly.

```python
# M1 — World State Engine
from modules.m1_world_state.main import (
    get_world_state,      # () -> WorldState: Read the current complete world state
    add_event,            # (event: WorldEvent) -> None: Add a world event
    update_agent,         # (agent: Agent) -> None: Update Agent state in the database
    get_tick,             # () -> int: Get the current tick count
)

# M2 — Agent System
from modules.m2_agent.main import (
    agent_think,          # (agent_id: str, context: str) -> str: Let the Agent think, returning the action description
    agent_act,            # (agent_id: str) -> WorldEvent: Let the Agent execute the action, returning the event
    update_agent_needs,   # (agent_id: str) -> None: Update Agent needs such as hunger/energy
    list_agents,          # () -> list[Agent]: List all alive Agents
)

# M3 — Memory System
from modules.m3_memory.main import (
    save_memory,          # (agent_id: str, event: str, importance: float) -> str: Store memory
    recall_memory,        # (agent_id: str, query: str, top_k: int = 5) -> list[str]: Semantically search memory
)

# M5 — Rules Engine
from modules.m5_rules.main import (
    validate_action,      # (agent: Agent, action: str) -> tuple[bool, str]: Validate if action is valid
    apply_resource_decay, # (world_state: WorldState) -> WorldState: Apply natural resource decay
    check_survival,       # (agent: Agent) -> bool: Check if Agent is alive
)
```

---

## Implementation Steps

### Step 1: Create File and Set Imports

Create `modules/m4_multi_agent/main.py` and add all necessary imports:

```python
# modules/m4_multi_agent/main.py

from shared.schemas import Agent, WorldEvent, WorldState

from modules.m1_world_state.main import (
    get_world_state,
    add_event,
    update_agent,
    get_tick,
)
from modules.m2_agent.main import (
    agent_think,
    agent_act,
    update_agent_needs,
    list_agents,
)
from modules.m3_memory.main import save_memory, recall_memory
from modules.m5_rules.main import validate_action, apply_resource_decay, check_survival
```

---

### Step 2: Implement `get_nearby_agents()`

Logic Description:
- Get current `WorldState` from `get_world_state()`
- Find `Location` corresponding to `agent_id` (get `x`, `y` coordinates)
- Traverse all other **alive** Agents, and calculate the Chebyshev distance (chessboard distance)
- distance ≤ `radius` and not oneself → add to return list

> [!TIP]
> Chebyshev distance formula: `max(|x1-x2|, |y1-y2|)`. This allows "adjacent" to include diagonal directions, conforming to intuitive chessboard movement.

```python
def get_nearby_agents(agent_id: str, radius: int = 1) -> list[Agent]:
    """Return all alive Agents within radius grids of the specified Agent"""
    world: WorldState = get_world_state()

    # TODO: Get the target Agent's position
    target_agent = world.agents.get(agent_id)
    if target_agent is None or not target_agent.is_alive:
        return []

    target_location = world.locations.get(target_agent.location_id)
    if target_location is None:
        return []

    nearby: list[Agent] = []

    for other_id, other_agent in world.agents.items():
        # TODO: Skip oneself and deceased Agents
        if other_id == agent_id or not other_agent.is_alive:
            continue

        # TODO: Calculate Chebyshev distance of the Locations of the two Agents
        other_location = world.locations.get(other_agent.location_id)
        if other_location is None:
            continue

        distance = max(
            abs(target_location.x - other_location.x),
            abs(target_location.y - other_location.y),
        )

        # TODO: If distance <= radius, add to list
        if distance <= radius:
            nearby.append(other_agent)

    return nearby
```

---

### Step 3: Implement `run_agent_interaction()`

Logic Description:
- Call `agent_think()` for each of the two Agents to think about the scenario of "encountering each other"
- Determine interaction type based on both parties' `personality.aggression`:
  - If either party has `aggression > 0.7` → `event_type = "conflict"`
  - Otherwise → `event_type = "interaction"`
- Create a `WorldEvent` describing this interaction
- Call `save_memory()` so both Agents remember this event
- Call `add_event()` to add the event to world history

```python
def run_agent_interaction(agent_id_1: str, agent_id_2: str) -> WorldEvent:
    """Drive two Agents to interact, returning the interaction event"""
    world: WorldState = get_world_state()
    current_tick: int = get_tick()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent does not exist: {agent_id_1} or {agent_id_2}")

    # TODO: Let each Agent think about the scenario of meeting the other
    context_1 = f"You met {agent2.name}, think about how you should respond."
    context_2 = f"You met {agent1.name}, think about how you should respond."

    thought_1 = agent_think(agent_id_1, context_1)
    thought_2 = agent_think(agent_id_2, context_2)

    # TODO: Determine interaction type based on aggression
    is_conflict = (
        agent1.personality.aggression > 0.7
        or agent2.personality.aggression > 0.7
    )
    event_type = "conflict" if is_conflict else "interaction"

    # TODO: Create WorldEvent
    description = (
        f"{agent1.name} and {agent2.name} had a {'clash' if is_conflict else 'interaction'}."
        f"({agent1.name}: {thought_1[:50]}...)"
        f"({agent2.name}: {thought_2[:50]}...)"
    )
    event = WorldEvent(
        tick=current_tick,
        event_type=event_type,
        description=description,
        affected_agent_ids=[agent_id_1, agent_id_2],
    )

    # TODO: Let both Agents remember this interaction
    importance = 0.8 if is_conflict else 0.5
    save_memory(agent_id_1, description, importance)
    save_memory(agent_id_2, description, importance)

    # TODO: Add event to world history
    add_event(event)

    return event
```

---

### Step 4: Implement `negotiate()`

Logic Description:
- Let each Agent `agent_think()`, using `topic` as the thinking context
- Calculate negotiation success rate based on personalities:
  - High `loyalty` → inclined to cooperate (increases success rate)
  - High `aggression` → inclined to clash (decreases success rate)
  - Recommended formula: `success_prob = (a1.loyalty + a2.loyalty) / 2 - (a1.aggression + a2.aggression) / 4`
- If successful (`success_prob > 0.5`):
  - Update the `relationships` scores of both Agents (add `+0.1` to each other, max `1.0`)
  - Call `update_agent()` to save the updated Agents
- Create negotiation memory and call `save_memory()`
- Return `{"success": bool, "outcome": str}`

> [IMPORTANT]
> Return format must strictly match `{"success": bool, "outcome": str}`. `outcome` is the text description of the negotiation result.

```python
def negotiate(agent_id_1: str, agent_id_2: str, topic: str) -> dict:
    """Drive two Agents to negotiate on a topic, returning the result {success: bool, outcome: str}"""
    world: WorldState = get_world_state()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent does not exist: {agent_id_1} or {agent_id_2}")

    # TODO: Let each Agent think about the topic
    context = f"You are negotiating with the other party on: {topic}. Express your stance."
    thought_1 = agent_think(agent_id_1, context)
    thought_2 = agent_think(agent_id_2, context)

    # TODO: Calculate success rate based on personality
    success_prob = (
        (agent1.personality.loyalty + agent2.personality.loyalty) / 2
        - (agent1.personality.aggression + agent2.personality.aggression) / 4
    )
    success = success_prob > 0.5

    # TODO: If negotiation succeeds, update relationship scores of both parties
    if success:
        current_rel_1_to_2 = agent1.relationships.get(agent_id_2, 0.0)
        current_rel_2_to_1 = agent2.relationships.get(agent_id_1, 0.0)

        agent1.relationships[agent_id_2] = min(1.0, current_rel_1_to_2 + 0.1)
        agent2.relationships[agent_id_1] = min(1.0, current_rel_2_to_1 + 0.1)

        update_agent(agent1)
        update_agent(agent2)

    # TODO: Create outcome description and memory
    outcome = (
        f"Negotiation {'successful' if success else 'failed'} (success rate: {success_prob:.2f})."
        f"Topic: {topic}."
        f"{agent1.name}'s stance: {thought_1[:50]}..."
        f"{agent2.name}'s stance: {thought_2[:50]}..."
    )

    importance = 0.7 if success else 0.4
    save_memory(agent_id_1, outcome, importance)
    save_memory(agent_id_2, outcome, importance)

    return {"success": success, "outcome": outcome}
```

---

### Step 5: Implement `run_tick()` (Core Main Flow)

`run_tick()` is the main function of M4, responsible for driving a complete tick. Please implement strictly according to the following process:

```
1. get_world_state() to get the current state
2. apply_resource_decay() to apply resource decay
3. For each alive Agent:
   a. update_agent_needs()
   b. check_survival() → if deceased, mark and create death event
   c. get_nearby_agents() to find nearby Agents
   d. If there are nearby Agents → run_agent_interaction()
   e. agent_act() → get action event
   f. validate_action() → if invalid, skip and record reason
   g. save_memory() to store memory
4. Collect all WorldEvents, call add_event()
5. Return all events in this tick
```

```python
def run_tick() -> list[WorldEvent]:
    """Execute a complete tick (all Agents act sequentially), returning all events in this tick"""
    tick_events: list[WorldEvent] = []
    current_tick: int = get_tick()

    # --- Step 1: Get current world state ---
    world: WorldState = get_world_state()

    # --- Step 2: Apply natural resource decay ---
    # TODO: Call apply_resource_decay(), passing the current WorldState
    world = apply_resource_decay(world)

    # --- Step 3: Execute action loop for each alive Agent ---
    agents: list[Agent] = list_agents()  # Only returns alive Agents

    for agent in agents:
        # --- 3a: Update Agent needs (hunger, energy, etc.) ---
        # TODO: Call update_agent_needs()
        update_agent_needs(agent.id)

        # --- Re-obtain latest Agent state (needs updated) ---
        refreshed_world = get_world_state()
        agent = refreshed_world.agents.get(agent.id)
        if agent is None:
            continue

        # --- 3b: Survival Check ---
        # TODO: Call check_survival(); if deceased, set is_alive=False and create death event
        is_alive = check_survival(agent)
        if not is_alive:
            agent.is_alive = False
            update_agent(agent)

            death_event = WorldEvent(
                tick=current_tick,
                event_type="death",
                description=f"{agent.name} died due to resource exhaustion.",
                affected_agent_ids=[agent.id],
                affected_location_ids=[agent.location_id],
            )
            add_event(death_event)
            tick_events.append(death_event)
            # Skip subsequent steps for this Agent after death
            continue

        # --- 3c: Find nearby Agents ---
        # TODO: Call get_nearby_agents(), radius=1
        nearby: list[Agent] = get_nearby_agents(agent.id, radius=1)

        # --- 3d: If there are nearby Agents, execute interaction ---
        # TODO: Call run_agent_interaction() on the first nearby Agent
        #       (Advanced: can interact with all nearby Agents, but avoid duplicate interactions)
        if nearby:
            interaction_target = nearby[0]
            try:
                interaction_event = run_agent_interaction(agent.id, interaction_target.id)
                tick_events.append(interaction_event)
            except Exception as e:
                print(f"[M4] Interaction failed: {agent.name} <-> {interaction_target.name}: {e}")

        # --- 3e: Let Agent execute action ---
        # TODO: Call agent_act(), getting action WorldEvent
        try:
            action_event: WorldEvent = agent_act(agent.id)
        except Exception as e:
            print(f"[M4] agent_act failed ({agent.name}): {e}")
            continue

        # --- 3f: Validate action validity ---
        # TODO: Call validate_action(); if invalid, skip this event (do not add to list)
        is_valid, reason = validate_action(agent, action_event.event_type)
        if not is_valid:
            print(f"[M4] Action invalid ({agent.name}): {reason}, skipping.")
            continue

        # Valid action: add to tick event list and write to world
        add_event(action_event)
        tick_events.append(action_event)

        # --- 3g: Store Memory ---
        # TODO: Call save_memory(), letting the Agent remember this action
        memory_text = f"Tick {current_tick}: {action_event.description}"
        save_memory(agent.id, memory_text, importance=0.5)

    return tick_events
```

---

## Verification Standards (Must pass all to be considered complete)

Please execute the following verifications in order, **all items must pass** to consider the development of M4 complete:

- [ ] **Environment verification**: `python -c "from modules.m4_multi_agent.main import run_tick, run_agent_interaction, negotiate, get_nearby_agents; print('import OK')"` outputs `import OK` without errors
- [ ] **`run_tick()` complete drive**: Prepare 3 alive Agents (at different Locations) in the test environment, calling `run_tick()` does not throw Exceptions, and successfully returns `list[WorldEvent]`
- [ ] **`run_tick()` returns at least 1 event**: `len(run_tick()) >= 1`
- [ ] **`get_nearby_agents()` only returns Agents at nearby locations**: Set Agent A at `(0,0)`, Agent B at `(0,1)`, Agent C at `(5,5)`; calling `get_nearby_agents(A.id, radius=1)` should only return B, not C
- [ ] **`get_nearby_agents()` does not return oneself**: The returned list does not contain the caller's Agent itself
- [ ] **`get_nearby_agents()` does not return deceased Agents**: Mark a nearby Agent `is_alive=False`, confirm it does not appear in the results
- [ ] **`run_agent_interaction()` returns valid WorldEvent**: Return value type is `WorldEvent`, `event_type` is `"interaction"` or `"conflict"`, and `affected_agent_ids` contains both Agents' ids
- [ ] **`negotiate()` returns valid format**: `result = negotiate(a1.id, a2.id, "resource allocation")`, confirm `result` is `dict` containing `"success"` (`bool`) and `"outcome"` (`str`) keys
- [ ] **relationship updated on negotiation success**: Run `negotiate()` between two Agents with high `loyalty` and low `aggression`, and confirm both parties' `relationships` scores are increased
- [ ] **Deceased Agent no longer participates in ticks**: After an Agent dies from resource depletion, its actions as the subject should not appear in the events returned by subsequent `run_tick()` calls (except for the death event itself)
- [ ] **Events written to M1**: After calling `run_tick()`, the length of `get_world_state().events` should increase, confirming events are indeed written via `add_event()`
- [ ] **Memory written to M3**: After calling `run_tick()`, calling `recall_memory(agent_id, "action", top_k=1)` for the acting Agent should retrieve at least one memory

---

## Appendix: Interaction Type Decision Logic Summary

| Scenario | Decision Condition | event_type | Memory Importance |
|------|----------|------------|------------|
| Normal Encounter | Both aggression ≤ 0.7 | `"interaction"` | 0.5 |
| Conflict Encounter | Either aggression > 0.7 | `"conflict"` | 0.8 |
| Agent Death | `check_survival()` returns False | `"death"` | — |

| Negotiation Result | Condition | relationship Change |
|----------|------|------------------|
| Success | `success_prob > 0.5` | Both parties +0.1 (max 1.0) |
| Failure | `success_prob <= 0.5` | No change |

> [NOTE]
> `success_prob` formula: `(loyalty1 + loyalty2) / 2 - (aggression1 + aggression2) / 4`
> The value range is approximately -0.15 to 0.75; 0.5 is a reasonable boundary.

---

*Document Version: 1.0 | Corresponding to Architecture.md last updated: 2026-05-25*
