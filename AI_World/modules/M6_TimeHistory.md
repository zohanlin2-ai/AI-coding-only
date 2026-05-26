# Module M6: Time & History

## Your Task

Implement the world's time advancement and history recording mechanisms, responsible for tick → season → year conversions, periodically saving world snapshots, and providing other modules with the ability to query past events and timelines.

---

## Scope of Responsibility

- **Responsible for:**
  - Manage the advancement logic of world time (tick, season, year)
  - Season switching rules (spring → summer → autumn → winter → spring)
  - Automatically save a world snapshot every 10 ticks
  - Force save a snapshot at the end of each season
  - Write (to `data/snapshots/snapshot_{tick}.json`) and read snapshots
  - Provide queries for historical events within a specified tick range
  - Provide a timeline of major events (`get_timeline()`)
  - Provide queries for the current season (`get_current_season()`)

- **Not responsible for:**
  - Execution of Agent behaviors (handled by M2, M4)
  - Applying resource decay rules (handled by M5; but M6 needs to prompt M5 when advancing ticks)
  - Management of vector memory (handled by M3)
  - Visualization interface (handled by M7)
  - Creation and deletion of Agents (handled by M2)

---

## Dependencies

- **Prerequisites:**
  - M0 (Generates `config.json`, M6 reads parameters like `tick_interval_sec`)
  - M1 (Provides `get_world_state()`, `get_tick()`, `save_state()`)
  - M3 (Provides `save_world_event()`, `search_history()`)

- **Used by the following modules:**
  - M7 (Streamlit visualization interface calls `get_timeline()` and `get_snapshot()` directly)
  - M8 (Integration tests call all M6 provided functions)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m6_time_history\
```

All code is written under this directory. When running the program, the **working directory (cwd) must be set to the project root directory**:
```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\
```
This ensures that imports such as `from shared.schemas import *` and `from modules.m1_world_state.main import ...` can be correctly resolved.

---

## Environment Setup

```bash
pip install pydantic
```

> **Note:** M1 and M3 have other dependencies (SQLite, ChromaDB, etc.). Please ensure their environments are also set up so M6 can call their functions correctly.

---

## Files to Create

```
AI_World/
├── modules/
│   └── m6_time_history/
│       └── main.py          ← The main file you need to implement
└── data/
    └── snapshots/           ← Snapshot output directory (automatically created when running, no manual creation needed)
        ├── snapshot_0.json
        ├── snapshot_10.json
        └── ...
```

> **No need to create the `data/snapshots/` directory**; it will be automatically created using `os.makedirs(..., exist_ok=True)` when the program starts.

---

## Shared Schema (Use directly, do not modify)

> Import from `shared/schemas.py`. **Do not define alternative classes yourself.**

The following are schemas that M6 will use:

```python
# shared/schemas.py (Excerpt)

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
    age: int = 0


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

> The following function names, parameter types, and return types **must not be changed**. The internal logic can be implemented freely.

```python
# modules/m6_time_history/main.py

def advance_tick() -> int:
    """Advance world time by one tick, update season/year, returning the new tick count"""

def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """Retrieve historical events within the specified tick range"""

def save_snapshot() -> None:
    """Save a snapshot of the current world state to data/snapshots/snapshot_{tick}.json"""

def get_snapshot(tick: int) -> Optional[WorldState]:
    """Retrieve the world snapshot for a specified tick, returning None if not found"""

def get_timeline() -> list[dict]:
    """Return a timeline list of all major events [{tick, event_type, description}]"""

def get_current_season() -> str:
    """Return the current season: 'spring' | 'summer' | 'autumn' | 'winter'"""
```

---

## External Functions You Can Call

```python
# Get world state and time from M1
from modules.m1_world_state.main import get_world_state, get_tick, save_state

# Access world event vector memory from M3
from modules.m3_memory.main import save_world_event, search_history
```

### External Function Descriptions

| Function | Description |
|------|------|
| `get_world_state() -> WorldState` | Read current complete world state (including all agents, events, etc.) |
| `get_tick() -> int` | Get current tick count |
| `save_state() -> None` | Serialize and save the current world state to M1's database |
| `save_world_event(event: WorldEvent) -> None` | Save the world event to ChromaDB for semantic search |
| `search_history(query: str, top_k: int = 10) -> list[WorldEvent]` | Semantically search historical events |

---

## Time Rules (Core Logic)

```
1 tick = 1 day

Every 30 ticks = 1 season, in the order of:
  spring (ticks 0~29) → summer (ticks 30~59) → autumn (ticks 60~89) → winter (ticks 90~119)

Every 120 ticks = 1 year (after running through 4 seasons, year +1, starting over from spring)

Season impact on resource decay (inform M5 or record in advance_tick):
  - winter: food decay +20%
  - summer: water decay +20%
  (M6 itself does not modify Agent resources directly; it should create a WorldEvent to inform M5 in advance_tick)
```

### Season Determination Formula

```python
SEASONS = ["spring", "summer", "autumn", "winter"]
TICKS_PER_SEASON = 30
TICKS_PER_YEAR = 120

def _calculate_season(tick: int) -> str:
    season_index = (tick % TICKS_PER_YEAR) // TICKS_PER_SEASON
    return SEASONS[season_index]

def _calculate_year(tick: int) -> int:
    return (tick // TICKS_PER_YEAR) + 1
```

---

## Snapshot Storage Format

- **Storage Location:** `data/snapshots/snapshot_{tick}.json`
- **Format:** JSON serialized from Pydantic `WorldState` (using `.model_dump_json()`)
- **Auto-save conditions:**
  1. Save once every 10 ticks (`tick % 10 == 0`)
  2. Force save at the end of each season (ticks 29, 59, 89, 119, 149..., i.e., `(tick + 1) % 30 == 0`)

---

## Implementation Steps

### Step 1: Create File and Basic Structure

Create `modules/m6_time_history/main.py` and write all imports and constant definitions first:

```python
# modules/m6_time_history/main.py

import os
import json
from typing import Optional
from datetime import datetime

from shared.schemas import WorldState, WorldEvent, gen_id
from modules.m1_world_state.main import get_world_state, get_tick, save_state
from modules.m3_memory.main import save_world_event, search_history

# ── Constants ──
SEASONS = ["spring", "summer", "autumn", "winter"]
TICKS_PER_SEASON = 30
TICKS_PER_YEAR = 120
SNAPSHOT_INTERVAL = 10
SNAPSHOT_DIR = "data/snapshots"

# ── Initialize Snapshot Directory ──
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
```

---

### Step 2: Implement Helper Functions (Private)

These functions are only used internally within the module and are prefixed with an underscore:

```python
def _calculate_season(tick: int) -> str:
    """Calculate current season based on tick"""
    # TODO: Calculate using SEASONS list and TICKS_PER_SEASON
    season_index = ...  # Hint: (tick % TICKS_PER_YEAR) // TICKS_PER_SEASON
    return SEASONS[season_index]


def _calculate_year(tick: int) -> int:
    """Calculate current year based on tick (starting from year 1)"""
    # TODO: Calculate year
    return ...  # Hint: (tick // TICKS_PER_YEAR) + 1


def _is_season_end(tick: int) -> bool:
    """Determine if current tick is the last day of a season"""
    # TODO: Conditions for the last day of a season
    return ...  # Hint: (tick + 1) % TICKS_PER_SEASON == 0


def _get_snapshot_path(tick: int) -> str:
    """Return the snapshot file path for a specified tick"""
    return os.path.join(SNAPSHOT_DIR, f"snapshot_{tick}.json")
```

---

### Step 3: Implement `advance_tick()`

This is the core function of M6, which needs to:
1. Get the current tick from M1
2. Calculate new tick, new season, new year
3. If season changes, create a `WorldEvent` record
4. Store the event in M3's vector memory
5. Trigger `save_snapshot()` at appropriate times
6. Call M1's `save_state()` to update database

```python
def advance_tick() -> int:
    """
    Advance world time by one tick, update season/year, returning the new tick count.

    Flow:
      1. Get current tick (from M1)
      2. new_tick = current_tick + 1
      3. Calculate new_season and new_year
      4. If season changes → create WorldEvent("season_change", ...), store in M3
      5. If new_tick % 10 == 0 → call save_snapshot()
      6. If _is_season_end(new_tick - 1) → call save_snapshot() (force save at season end)
      7. Call M1's save_state()
      8. Return new_tick
    """
    current_tick = get_tick()
    new_tick = current_tick + 1

    old_season = _calculate_season(current_tick)
    new_season = _calculate_season(new_tick)
    new_year = _calculate_year(new_tick)

    # TODO: Create WorldEvent and store in M3 when season changes
    if new_season != old_season:
        event = WorldEvent(
            tick=new_tick,
            event_type=...,        # Fill in appropriate event_type
            description=...,       # For example: f"Season changed to {new_season} in year {new_year}"
        )
        save_world_event(event)

    # TODO: Determine if snapshot storage is needed
    # Condition 1: Every 10 ticks
    # Condition 2: At season end (use _is_season_end)

    # TODO: Call M1's save_state()

    return new_tick
```

> **Hint:** M1's `WorldState` has `tick`, `season`, and `year` fields, but M6 does not modify the WorldState object directly — it persists it via M1's `save_state()`. If M1's `save_state()` does not automatically update tick/season/year, verify M1's implementation and, if necessary, update the WorldState object here first before calling `save_state()`.

---

### Step 4: Implement `save_snapshot()` and `get_snapshot()`

```python
def save_snapshot() -> None:
    """
    Save the current world state as a JSON snapshot.

    Flow:
      1. Call M1's get_world_state() to get complete state
      2. Use WorldState.model_dump_json() for serialization
      3. Write to data/snapshots/snapshot_{tick}.json
    """
    world_state = get_world_state()
    tick = world_state.tick
    path = _get_snapshot_path(tick)

    # TODO: Serialize and write to file
    json_str = world_state.model_dump_json(indent=2)
    with open(path, "w", encoding="utf-8") as f:
        ...


def get_snapshot(tick: int) -> Optional[WorldState]:
    """
    Read the snapshot for a specified tick, returning None if not found.

    Flow:
      1. Calculate file path using _get_snapshot_path(tick)
      2. If file does not exist → return None
      3. Read JSON → Parse using WorldState.model_validate_json()
      4. Return WorldState object
    """
    path = _get_snapshot_path(tick)

    if not os.path.exists(path):
        return None

    # TODO: Read and parse JSON
    with open(path, "r", encoding="utf-8") as f:
        ...

    return ...  # WorldState object
```

---

### Step 5: Implement `get_history()`

```python
def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """
    Retrieve all world events in the range from start_tick to end_tick (inclusive).

    Strategy:
      1. Call M1's get_world_state(), getting all events from world_state.events
      2. Filter events with ticks in the [start_tick, end_tick] range
      3. Return sorted by tick

    Note: If M1 does not store the complete event list, consider scanning snapshot files to merge events.
    """
    world_state = get_world_state()

    # TODO: Filter and sort events
    filtered = [
        event for event in world_state.events
        if start_tick <= event.tick <= end_tick
    ]

    return sorted(filtered, key=lambda e: e.tick)
```

---

### Step 6: Implement `get_timeline()`

```python
def get_timeline() -> list[dict]:
    """
    Return a timeline list of all major events.

    Each item format:
      {
        "tick": int,
        "event_type": str,
        "description": str
      }

    Major event definition (choose any of the following strategies):
      - Strategy A: Return all events with event_type "season_change", "conflict", "death", "discovery"
      - Strategy B: Return all events in world_state.events (sorted by tick)
      - Strategy C: Aggregate by scanning snapshot files

    It is recommended to use Strategy A to only show "meaningful" events on the timeline.
    """
    world_state = get_world_state()

    MAJOR_EVENT_TYPES = {"season_change", "conflict", "death", "discovery"}

    # TODO: Filter major events and format output
    timeline = []
    for event in sorted(world_state.events, key=lambda e: e.tick):
        if event.event_type in MAJOR_EVENT_TYPES:
            timeline.append({
                "tick": event.tick,
                "event_type": event.event_type,
                "description": event.description,
            })

    return timeline
```

---

### Step 7: Implement `get_current_season()`

```python
def get_current_season() -> str:
    """
    Return current season string.

    Flow:
      1. Call M1's get_tick() to get tick
      2. Calculate season using _calculate_season(tick)
      3. Return season string
    """
    tick = get_tick()
    return _calculate_season(tick)
```

---

### Step 8: Module-Level Initialization (Optional)

If any initialization is needed when the module is imported (e.g., ensuring snapshot directory exists), add to the very top or bottom of the file:

```python
# Ensure snapshot directory exists (already executed in constant definitions, this is backup)
def _ensure_snapshot_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

_ensure_snapshot_dir()
```

---

## Verification Standards (Must pass all to be considered complete)

> Run the following tests under the project root (`AI_World/`):

- [ ] **`advance_tick()` return value is correct**
  - Call `advance_tick()` 3 times consecutively; each return value should be 1 greater than the previous one
  - `advance_tick()` should return `int` type

- [ ] **Season switching is correct**
  - When advancing from tick 0 to tick 30, `get_current_season()` should change from `"spring"` to `"summer"`
  - When advancing from tick 90 to tick 120, it should change from `"winter"` to `"spring"` and year +1

- [ ] **`get_history(0, 10)` works normally**
  - Calling `get_history(0, 10)` should return `list[WorldEvent]` (can be empty but must not error)
  - The returned events' ticks must all be in the `[0, 10]` range

- [ ] **`save_snapshot()` generates JSON file**
  - After calling `save_snapshot()`, `data/snapshots/snapshot_{tick}.json` should exist
  - File content must be valid JSON and parseable with `WorldState.model_validate_json()`

- [ ] **`get_snapshot(tick)` can read back snapshot**
  - Calling `save_snapshot()` first and then calling `get_snapshot(current_tick)` should return a `WorldState` object
  - Calling `get_snapshot(99999)` should return `None` (non-existent tick)

- [ ] **`get_timeline()` format is correct**
  - Calling `get_timeline()` should return `list[dict]`
  - Each dict must contain three keys: `"tick"`, `"event_type"`, and `"description"`
  - tick value is `int`, event_type and description are `str`

- [ ] **`get_current_season()` returns correct string**
  - The return value must be one of `"spring"`, `"summer"`, `"autumn"`, `"winter"`
  - Must not return other strings or `None`

- [ ] **Auto-save snapshot triggered**
  - When advancing to the 10th tick, `data/snapshots/snapshot_10.json` should automatically exist
  - When advancing to the 29th tick (end of spring), the corresponding snapshot should exist

- [ ] **Does not affect existing modules**
  - Importing `modules.m6_time_history.main` does not trigger side effects (does not modify database)
  - Any module-level initialization should only create directories and not modify world state

---

## FAQ

**Q: Does `advance_tick()` need to modify the tick value in M1's database?**

**A:** Yes, verify if M1's `save_state()` saves tick/season/year. If these fields in M1's WorldState object are in-memory only, M6 needs to update the WorldState object first (modify `.tick`, `.season`, `.year`), then call `save_state()`.

**Q: What if the events list in M1 for `get_history()` is too long?**

**A:** For the current MVP stage, filtering directly from memory is sufficient. If performance becomes an issue in the future, it can be changed to scan snapshot files.

**Q: Saved every 10 ticks; if tick 10 is also the end of a season, how many times is it saved?**

**A:** Only once. When both conditions are met, call `save_snapshot()` once (the function itself is idempotent).

**Q: Will there be issues with datetime fields in the snapshot JSON format?**

**A:** Pydantic v2's `model_dump_json()` automatically handles `datetime` serialization. Reading with `model_validate_json()` parses it correctly without manual handling.

---

*Document Version: 1.0 | Last Updated: 2026-05-25*
