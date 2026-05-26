# Module M5: Rules Engine

## Your Task

Implement the underlying world rules engine, responsible for validating whether all Agent actions are valid, applying resource decay and regeneration rules per tick, executing economic logic, and checking whether Agents are alive, ensuring the world does not collapse due to out-of-control AI behavior.

---

## Scope of Responsibility

- **Responsible for:**
  - Define and manage all underlying game rules (resource decay, action validity, economic constraints)
  - Validate whether the Agent's action string complies with rules, returning approval/rejection and reasons
  - Apply natural resource decay to each Agent per tick (food, water, energy decrease)
  - Apply natural resource regeneration for locations per tick (each location +2, max 1000)
  - Apply economic rules such as transaction fees (10%) and ensuring money does not become negative
  - Determine whether an Agent dies due to resource exhaustion (food <= 0 or water <= 0)
  - Provide a summary of all rules (for M7 visualization or M8 integration testing)

- **Not responsible for:**
  - Saving world state to the database (handled by M1)
  - Driving Agent thinking or actions (handled by M2)
  - Managing tick advancement (handled by M6)
  - Executing actual resource transfers for transactions (handled by M4, M5 only validates)
  - Memory system (handled by M3)

---

## Dependencies

- **Prerequisites:**
  - M0 (Provides `config.json`)
  - M1 (Provides `get_world_state()`, M5 reads world state as basis for validation)

- **Used by the following modules:**
  - M2 (Calls `validate_action()` before Agent actions)
  - M4 (Calls `validate_action()`, `apply_resource_decay()`, `apply_economic_rules()` during multi-agent interaction)
  - M6 (Calls `apply_resource_decay()`, `check_survival()` per tick)
  - M8 (Calls all provided functions during integration testing)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m5_rules\
```

---

## Environment Setup

```bash
pip install pydantic
```

> **Note:** This module uses **Pydantic v2**. Please verify the version:
> ```bash
> python -c "import pydantic; print(pydantic.__version__)"
> ```
> The version should be `2.x.x`.

---

## Files to Create

```
AI_World/
└── modules/
    └── m5_rules/
        └── main.py          ← The only file to create
```

> **Note:** No need to create `__init__.py`, import directly from `modules/m5_rules/main.py`.

---

## Shared Schema (Use directly, do not modify)

> Must import from `shared/schemas.py`. **Do not redefine these classes in `m5_rules/main.py`.**

```python
# The complete content of shared/schemas.py (for reference only, import directly for use)

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


class Location(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    x: int
    y: int
    terrain: str  # "plains" | "mountain" | "forest" | "water"
    resources: Resource = Field(default_factory=Resource)


class AgentPersonality(BaseModel):
    hunger: float = 0.3
    fear: float = 0.3
    ambition: float = 0.5
    loyalty: float = 0.5
    aggression: float = 0.3


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
    age: int = 0  # Unit: tick


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

---

## Provided Functions (Signatures cannot be modified)

> These functions are the public commitment of M5 to other modules. **Function names, parameter types, and return types must not be changed.** The internal logic can be implemented freely.

```python
def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """
    Validate whether the Agent's action string is valid.
    - Returns (True, "") if the action is valid and can be executed
    - Returns (False, "Reason description") if the action is invalid, explaining the reason
    """

def apply_resource_decay(world_state: WorldState) -> WorldState:
    """
    Apply natural resource decay rules to all alive Agents per tick, as well as natural regeneration for locations.
    Returns the updated WorldState (not directly written to database, caller decides whether to save).
    """

def check_survival(agent: Agent) -> bool:
    """
    Check if the Agent is alive.
    - food <= 0 or water <= 0 → returns False (deceased)
    - Otherwise returns True (alive)
    """

def apply_economic_rules(world_state: WorldState) -> WorldState:
    """
    Apply economic rules, ensuring location resources do not exceed maximums, money does not become negative, etc.
    Returns the updated WorldState.
    """

def get_rules_summary() -> dict:
    """
    Return a summary dict of all rules, for visualization or integration testing.
    Example format:
    {
        "resource_decay": {...},
        "action_rules": {...},
        "economic_rules": {...},
        "survival_rules": {...}
    }
    """
```

---

## External Functions You Can Call

```python
# Get current world state from M1 (if terrain information is needed for action validation)
from modules.m1_world_state.main import get_world_state
```

> **Usage Notes:**
> - `get_world_state()` returns a `WorldState` object
> - Get location terrain info: `world_state.locations[location_id].terrain`
> - Get whether location exists: `location_id in world_state.locations`
> - **Do not operate the database directly in M5**, only obtain data through the M1 interface

---

## Rule Definitions (Complete Specification)

### 1. Resource Decay Rules (Applied per tick by `apply_resource_decay`)

| Resource | Base Decay | Special Conditions |
|------|---------|---------|
| food | -5 / tick | -3 if Agent's location terrain is `forest` (forests have wild food) |
| water | -4 / tick | No special conditions |
| energy | -3 / tick | -1 if Agent is in "resting" state (resting decays less) |
| money | No natural decay | Only changes during transactions |
| materials | No natural decay | Only changes during actions |

> **Determining "resting state":** Parse the most recent action string. If it contains `"休息"` or `"rest"`, it is treated as a resting state. If unable to determine, default to the base decay value (-3).

### 2. Action Validation Rules (Checked by `validate_action`)

| Action Keyword | Valid Conditions | Error Message when Invalid |
|-----------|---------|----------------|
| `採集食物` | Agent's location terrain must be `forest` or `plains` | `"Gathering food can only be executed in forest or plains terrain"` |
| `移動` | The target location ID in the action string must exist in the WorldState | `"Target location does not exist in the world"` |
| `交易` | Must specify target; money of both parties must not be negative after deduction | `"Trade partner not specified"` or `"Insufficient resources, cannot trade"` |
| Any Action | Agent's money must not become negative after execution | `"Executing this action will lead to negative money"` |

> **Action String Parsing Notes:**
> - Action strings are natural language descriptions generated by LLM, e.g., `"I want to move to loc_abc1"`, `"I want to gather food"`, `"I want to trade 20 food with Agent_xyz"`
> - Use `in` operator or `str.find()` for keyword matching, complex parsing is not required
> - Unrecognized action types default to returning `(True, "")` allowing execution

### 3. Economic Rules (Applied by `apply_economic_rules`)

| Rule | Description |
|------|------|
| Transaction Fee | Charge 10% of the trade amount during transactions, deducted from money |
| Location Resource Cap | Every resource field of each Location has a cap of 1000.0 |
| Natural Resource Regeneration | food/water/materials at each location regenerate +2 per tick (not exceeding cap) |
| Money Lower Bound | Under any circumstances, Agent's money must not be lower than 0.0 |

---

## Implementation Steps

### Step 1: Create File and Set Imports

In `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m5_rules\main.py`, create the following skeleton:

```python
# modules/m5_rules/main.py
"""
M5 — Rules Engine
Responsible for: action validation, resource decay, survival check, economic rules
"""

import sys
import os

# Make shared/ and modules/ discoverable for Python
# This module is run from AI_World/ root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from shared.schemas import Agent, WorldState, Resource, Location, WorldEvent
from modules.m1_world_state.main import get_world_state

# --- Constant Definitions (Centralized Rule Parameter Management) ---

# Resource Decay Rules
FOOD_DECAY_DEFAULT = 5.0       # Base decay per tick on normal terrain
FOOD_DECAY_FOREST = 3.0        # Decay per tick in forest terrain (wild food available)
WATER_DECAY = 4.0              # Decay per tick
ENERGY_DECAY_DEFAULT = 3.0     # Decay per tick in normal state
ENERGY_DECAY_RESTING = 1.0     # Decay per tick in resting state

# Economic Rules
TRADE_FEE_RATE = 0.10          # Transaction fee rate 10%
LOCATION_RESOURCE_MAX = 1000.0 # Location resource cap
RESOURCE_REGEN_PER_TICK = 2.0  # Location resource regeneration amount per tick
MONEY_MIN = 0.0                # Minimum money value
```

---

### Step 2: Implement `validate_action()`

```python
def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """
    Validate whether the Agent's action string is valid.
    Returns (True, "") if allowed; returns (False, "reason") if rejected.
    """
    # 1. Get the current world state (for terrain and location validation)
    world_state = get_world_state()

    # 2. Get the terrain of the Agent's current location
    current_location = world_state.locations.get(agent.location_id)
    current_terrain = current_location.terrain if current_location else "unknown"

    # 3. Gather Food: only in forest or plains
    if "採集食物" in action:
        # TODO: Check if current_terrain is "forest" or "plains"
        # If not, return (False, "Gathering food can only be executed in forest or plains terrain")
        pass

    # 4. Move: target location must exist
    if "移動" in action:
        # TODO: Parse target location ID from action string
        # Hint: Can split action string and search for token that resembles location_id
        # If target location is not in world_state.locations, return (False, "Target location does not exist in the world")
        pass

    # 5. Trade: must specify partner and cannot let money become negative
    if "交易" in action:
        # TODO: Check if action mentions trading partner (contains Agent id or name)
        # TODO: Try to parse trading amount, ensuring agent.resources.money - amount >= MONEY_MIN
        # If amount is unclear, default to allow (return True)
        pass

    # 6. General Rule: any action must not make money negative
    # (Conservative estimate, skip if amount cannot be parsed)

    # 7. All rules passed, allow action
    return (True, "")
```

---

### Step 3: Implement `apply_resource_decay()`

```python
def apply_resource_decay(world_state: WorldState) -> WorldState:
    """
    Apply natural resource decay (to Agent) and natural regeneration (to location) per tick.
    Modifies the passed WorldState directly and returns it.
    """
    # --- Apply Resource Decay to Each Alive Agent ---
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue  # Skip deceased Agents

        # 1. Get the terrain of Agent's location
        location = world_state.locations.get(agent.location_id)
        terrain = location.terrain if location else "unknown"

        # 2. Calculate food decay
        # TODO: Use FOOD_DECAY_FOREST if terrain == "forest", otherwise FOOD_DECAY_DEFAULT
        food_decay = ...

        # 3. Calculate energy decay
        # TODO: Parse Agent's latest action (this info cannot be obtained directly from WorldState for now)
        # Temporary: if Agent has no memory, default to ENERGY_DECAY_DEFAULT
        # Advanced: can look for latest event related to this Agent in WorldState.events,
        #           if latest event description contains "休息" or "rest", use ENERGY_DECAY_RESTING
        energy_decay = ...

        # 4. Apply decay (resource values must not be lower than 0)
        # TODO: Update agent.resources.food, water, energy
        # agent.resources.food = max(0.0, agent.resources.food - food_decay)
        # agent.resources.water = max(0.0, agent.resources.water - WATER_DECAY)
        # agent.resources.energy = max(0.0, agent.resources.energy - energy_decay)

        # 5. Update Agent in WorldState
        world_state.agents[agent_id] = agent

    # --- Apply Natural Resource Regeneration to Each Location ---
    for loc_id, location in world_state.locations.items():
        # TODO: Add RESOURCE_REGEN_PER_TICK to food, water, materials,
        #       but do not exceed LOCATION_RESOURCE_MAX
        # location.resources.food = min(LOCATION_RESOURCE_MAX, location.resources.food + RESOURCE_REGEN_PER_TICK)
        # Same for water, materials
        world_state.locations[loc_id] = location

    return world_state
```

---

### Step 4: Implement `check_survival()`

```python
def check_survival(agent: Agent) -> bool:
    """
    Check if the Agent is alive.
    - food <= 0 or water <= 0 → deceased, returns False
    - Otherwise returns True
    """
    # TODO: Check agent.resources.food and agent.resources.water
    # If either <= 0, return False
    # Otherwise return True
    pass
```

---

### Step 5: Implement `apply_economic_rules()`

```python
def apply_economic_rules(world_state: WorldState) -> WorldState:
    """
    Apply economic rules:
    1. Ensure all Agents' money is not lower than MONEY_MIN (0.0)
    2. Ensure all locations' resources do not exceed LOCATION_RESOURCE_MAX (1000.0)
    3. Transaction fees are handled by validate_action / M4 during trading,
       this function does clean-up afterward (clamped between 0 and upper bound)
    """
    # --- For Each Agent ---
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue

        # TODO: Ensure money is not negative
        # agent.resources.money = max(MONEY_MIN, agent.resources.money)

        world_state.agents[agent_id] = agent

    # --- For Each Location ---
    for loc_id, location in world_state.locations.items():
        # TODO: Ensure all resource fields are between [0, LOCATION_RESOURCE_MAX]
        # location.resources.food = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.food))
        # Same for water, energy, money, materials
        world_state.locations[loc_id] = location

    return world_state
```

---

### Step 6: Implement `get_rules_summary()`

```python
def get_rules_summary() -> dict:
    """
    Return a dict summary of all rules, for visualization (M7) or integration testing (M8).
    """
    return {
        "resource_decay": {
            "food_decay_default": FOOD_DECAY_DEFAULT,
            "food_decay_forest": FOOD_DECAY_FOREST,
            "water_decay": WATER_DECAY,
            "energy_decay_default": ENERGY_DECAY_DEFAULT,
            "energy_decay_resting": ENERGY_DECAY_RESTING,
            "description": "Applies resource decay to alive Agents per tick; forest terrain consumes less food; resting state consumes less energy"
        },
        "action_rules": {
            # TODO: Supplement action validation rule descriptions
            "採集食物": "Gathering food can only be executed in forest or plains terrain",
            "移動": "Target location must exist in the world",
            "交易": "Must specify partner, and both parties must have sufficient resources",
            "通用": "Any action must not make money lower than 0"
        },
        "economic_rules": {
            "trade_fee_rate": TRADE_FEE_RATE,
            "location_resource_max": LOCATION_RESOURCE_MAX,
            "resource_regen_per_tick": RESOURCE_REGEN_PER_TICK,
            "money_min": MONEY_MIN,
            "description": "Transactions collect 10% fee; location resource cap 1000; location resources naturally regenerate +2 per tick"
        },
        "survival_rules": {
            "death_conditions": ["food <= 0", "water <= 0"],
            "description": "Agent dies when food or water is depleted"
        }
    }
```

---

### Step 7: Add Helper Functions (Optional, improves readability)

The following are suggested private helper functions, placed before external functions:

```python
def _get_agent_terrain(agent: Agent, world_state: WorldState) -> str:
    """Get terrain of the location where Agent is, returns 'unknown' if location does not exist"""
    location = world_state.locations.get(agent.location_id)
    return location.terrain if location else "unknown"


def _is_agent_resting(agent: Agent, world_state: WorldState) -> bool:
    """
    Check if the Agent is in a resting state.
    Strategy: Find the most recent event related to this Agent in WorldState.events,
    if description contains '休息' or 'rest', return True.
    """
    # Find backward from the newest event
    for event in reversed(world_state.events):
        if agent.id in event.affected_agent_ids:
            desc = event.description.lower()
            if "休息" in desc or "rest" in desc:
                return True
            else:
                return False  # Found recent event but not resting
    return False  # No historical events, default to non-resting


def _parse_trade_amount(action: str) -> float:
    """
    Parse trade amount from action string.
    E.g., "I want to trade 20 food with Agent_xyz" → returns 20.0
    If parsing fails, returns 0.0
    """
    # TODO: Parse numbers using re or split
    import re
    numbers = re.findall(r'\d+\.?\d*', action)
    if numbers:
        return float(numbers[0])
    return 0.0
```

---

### Step 8: Verify Import Paths are Correct

Before running any tests, confirm that Python can find `shared.schemas` and `modules.m1_world_state.main`:

```python
# Execute at AI_World/ root directory
python -c "from modules.m5_rules.main import get_rules_summary; print(get_rules_summary())"
```

If `ModuleNotFoundError` occurs, confirm:
1. You are running Python in `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\`
2. `shared/schemas.py` exists
3. `sys.path.insert(0, ROOT_DIR)` in `m5_rules/main.py` is configured correctly

---

## Verification Standards (Must pass all to be considered complete)

Please execute the following tests one by one to verify the results are as expected. **All must pass to be considered complete.**

```python
# Verification script: Run at AI_World/ root directory
# python verify_m5.py

from shared.schemas import Agent, AgentPersonality, Resource, Location, WorldState
from modules.m5_rules.main import (
    validate_action,
    apply_resource_decay,
    check_survival,
    apply_economic_rules,
    get_rules_summary
)

print("=== M5 Rules Engine Verification ===\n")

# ── --- Create Test Data --- ──────────────────────────────────────────────────

forest_location = Location(id="loc_forest", name="Deep Forest", x=0, y=0, terrain="forest")
plains_location = Location(id="loc_plains", name="Open Plains", x=1, y=0, terrain="plains")
mountain_location = Location(id="loc_mountain", name="High Mountain", x=2, y=0, terrain="mountain")

test_agent = Agent(
    id="agent_001",
    name="TestAgent",
    location_id="loc_plains",
    resources=Resource(food=50.0, water=50.0, energy=50.0, money=100.0, materials=20.0)
)

world = WorldState(
    tick=1,
    locations={
        "loc_forest": forest_location,
        "loc_plains": plains_location,
        "loc_mountain": mountain_location,
    },
    agents={"agent_001": test_agent}
)

# ── --- Verification 1: validate_action() returns (False, reason) for invalid actions --- ──────

# Test 1a: Gather food in mountain (invalid)
agent_in_mountain = test_agent.model_copy(update={"location_id": "loc_mountain"})
ok, reason = validate_action(agent_in_mountain, "我要採集食物")
assert ok == False, "❌ Test 1a failed: Gathering food in mountain should be rejected"
assert reason != "", "❌ Test 1a failed: Rejection reason must not be an empty string"
print(f"✅ Test 1a passed: Gathering food in mountain rejected, reason: {reason}")

# Test 1b: Move to non-existent location (invalid)
ok, reason = validate_action(test_agent, "我要移動到 loc_nonexistent")
assert ok == False, "❌ Test 1b failed: Moving to non-existent location should be rejected"
print(f"✅ Test 1b passed: Moving to non-existent location rejected, reason: {reason}")

# ── --- Verification 2: validate_action() returns (True, "") for valid actions --- ──────────────

# Test 2a: Gather food in forest (valid)
agent_in_forest = test_agent.model_copy(update={"location_id": "loc_forest"})
ok, reason = validate_action(agent_in_forest, "我要採集食物")
assert ok == True, f"❌ Test 2a failed: Gathering food in forest should be allowed, but rejected: {reason}"
assert reason == "", f"❌ Test 2a failed: Reason for valid action should be empty, but got: {reason}"
print(f"✅ Test 2a passed: Gathering food in forest is allowed")

# Test 2b: Gather food in plains (valid)
ok, reason = validate_action(test_agent, "我要採集食物")  # test_agent is in plains
assert ok == True, f"❌ Test 2b failed: Gathering food in plains should be allowed"
print(f"✅ Test 2b passed: Gathering food in plains is allowed")

# Test 2c: Move to existing location (valid)
ok, reason = validate_action(test_agent, "我要移動到 loc_forest")
assert ok == True, f"❌ Test 2c failed: Moving to existing location should be allowed, but rejected: {reason}"
print(f"✅ Test 2c passed: Moving to existing location is allowed")

# ── --- Verification 3: Resources decrease correctly after apply_resource_decay() --- ──────────────────

import copy
world_copy = copy.deepcopy(world)  # test_agent is in plains
world_after = apply_resource_decay(world_copy)
agent_after = world_after.agents["agent_001"]

# Food in plains terrain should decrease by 5 (50 - 5 = 45)
assert agent_after.resources.food == 45.0, \
    f"❌ Test 3a failed: Food in plains terrain should be 45.0, actual: {agent_after.resources.food}"
print(f"✅ Test 3a passed: Food in plains terrain decayed 5, result {agent_after.resources.food}")

# Water should decrease by 4 (50 - 4 = 46)
assert agent_after.resources.water == 46.0, \
    f"❌ Test 3b failed: Water should be 46.0, actual: {agent_after.resources.water}"
print(f"✅ Test 3b passed: Water decayed 4, result {agent_after.resources.water}")

# Food in forest terrain should only decrease by 3
world_forest = WorldState(
    tick=1,
    locations={"loc_forest": forest_location},
    agents={"agent_002": Agent(
        id="agent_002", name="ForestAgent", location_id="loc_forest",
        resources=Resource(food=50.0, water=50.0, energy=50.0, money=100.0)
    )}
)
world_forest_after = apply_resource_decay(world_forest)
forest_agent_after = world_forest_after.agents["agent_002"]
assert forest_agent_after.resources.food == 47.0, \
    f"❌ Test 3c failed: Food in forest terrain should be 47.0, actual: {forest_agent_after.resources.food}"
print(f"✅ Test 3c passed: Food in forest terrain only decayed 3, result {forest_agent_after.resources.food}")

# ── --- Verification 4: check_survival() returns False when food <= 0 --- ──────────────

dead_by_food = test_agent.model_copy(
    update={"resources": Resource(food=0.0, water=50.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_food) == False, "❌ Test 4a failed: food=0 should return False"
print(f"✅ Test 4a passed: food=0 returns False (death)")

dead_by_water = test_agent.model_copy(
    update={"resources": Resource(food=50.0, water=0.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_water) == False, "❌ Test 4b failed: water=0 should return False"
print(f"✅ Test 4b passed: water=0 returns False (death)")

healthy_agent = test_agent.model_copy(
    update={"resources": Resource(food=10.0, water=10.0, energy=50.0, money=100.0)}
)
assert check_survival(healthy_agent) == True, "❌ Test 4c failed: food=10 water=10 should return True"
print(f"✅ Test 4c passed: food=10 water=10 returns True (alive)")

# ── --- Verification 5: apply_economic_rules() ensures money is not negative --- ──────────────

negative_money_agent = test_agent.model_copy(
    update={"resources": Resource(food=50.0, water=50.0, energy=50.0, money=-10.0)}
)
world_eco = WorldState(
    tick=1,
    locations={"loc_plains": plains_location},
    agents={"agent_eco": negative_money_agent.model_copy(update={"id": "agent_eco", "location_id": "loc_plains"})}
)
world_eco_after = apply_economic_rules(world_eco)
assert world_eco_after.agents["agent_eco"].resources.money >= 0.0, \
    f"❌ Test 5 failed: money should be >= 0 after apply_economic_rules, actual: {world_eco_after.agents['agent_eco'].resources.money}"
print(f"✅ Test 5 passed: apply_economic_rules ensures money >= 0")

# ── --- Verification 6: get_rules_summary() returns dict containing necessary keys --- ──────────────

summary = get_rules_summary()
assert isinstance(summary, dict), "❌ Test 6 failed: get_rules_summary() should return dict"
required_keys = ["resource_decay", "action_rules", "economic_rules", "survival_rules"]
for key in required_keys:
    assert key in summary, f"❌ Test 6 failed: summary lacks key '{key}'"
print(f"✅ Test 6 passed: get_rules_summary() returns dict containing all required keys")

print("\n🎉 All M5 verifications passed!")
```

### Run Verification

```bash
# Execute at AI_World/ root directory
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World
python verify_m5.py
```

Expected output (All ✅):

```
=== M5 Rules Engine Verification ===

✅ Test 1a passed: Gathering food in mountain rejected, reason: Gathering food can only be executed in forest or plains terrain
✅ Test 1b passed: Moving to non-existent location rejected, reason: Target location does not exist in the world
✅ Test 2a passed: Gathering food in forest is allowed
✅ Test 2b passed: Gathering food in plains is allowed
✅ Test 2c passed: Moving to existing location is allowed
✅ Test 3a passed: Food in plains terrain decayed 5, result 45.0
✅ Test 3b passed: Water decayed 4, result 46.0
✅ Test 3c passed: Food in forest terrain only decayed 3, result 47.0
✅ Test 4a passed: food=0 returns False (death)
✅ Test 4b passed: water=0 returns False (death)
✅ Test 4c passed: food=10 water=10 returns True (alive)
✅ Test 5 passed: apply_economic_rules ensures money >= 0
✅ Test 6 passed: get_rules_summary() returns dict containing all required keys

🎉 All M5 verifications passed!
```

---

## Warnings and Common Mistakes

> [IMPORTANT]
> **Do not directly read/write the database within M5.** All data access must go through M1's `get_world_state()`. After M5's functions modify the `WorldState` object, it is up to the caller (M4/M6) to decide whether to call M1's `update_agent()` or `save_state()` to save.

> [WARNING]
> **`apply_resource_decay()` and `apply_economic_rules()` modify the passed `WorldState` object.** If the caller needs to keep the original state for comparison, they must perform `copy.deepcopy(world_state)` themselves before calling.

> [TIP]
> For action string parsing, it is recommended to use the `in` keyword instead of complex regular expressions. This prevents failures if the LLM output format changes slightly. E.g., `if "gather food" in action` is more robust than `re.match(r'gather food', action)`.

> [NOTE]
> `validate_action()` calls `get_world_state()` every time it is invoked. If M1 is not completed, this function cannot be used. Please ensure M1 is completed and working normally.

---

*Document Version: 1.0 | Corresponding to Architecture.md last updated: 2026-05-25*
