# Module M2: Agent System

## Your Task

Create and manage AI Agents, enabling each Agent to think (`agent_think`) and act (`agent_act`) via the local Ollama LLM, and write the action results into the M1 world state as `WorldEvent`s.

---

## Scope of Responsibility

- **Responsible for:**
  - Create Agents and store them in the M1 world state
  - Assemble Agent thinking prompts and call the Ollama LLM
  - Parse LLM outputs and convert them into valid actions
  - Execute actions (update resources, locations) and generate `WorldEvent`s
  - Update Agent needs such as `hunger` and `energy` every tick
  - Validate action validity and check survival status via M5

- **Not responsible for:**
  - Persistence of the world state (handled by M1)
  - Memory vector search and storage low-level layer (handled by M3)
  - Interaction scheduling among multiple Agents (handled by M4)
  - Rule definition and application (handled by M5)
  - Time advancement (handled by M6)

---

## Dependencies

- **Prerequisites:**
  - M0 (`config.json` must exist)
  - M1 (`get_world_state`, `update_agent`, `add_event` must be callable)
  - M3 (`get_recent_memory`, `save_memory` must be callable)
  - M5 (`validate_action`, `check_survival` must be callable)

- **Used by the following modules:**
  - M4 (Calls `agent_think`, `agent_act`, `list_agents`)
  - M8 (Integration Testing)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m2_agent\
```

> **Note**: All `import` paths are executed with `AI_World/` as the root directory, e.g.:
> ```bash
> # Run under AI_World/ directory
> python -m modules.m2_agent.main
> ```

---

## Environment Setup

```bash
pip install requests pydantic
```

> `requests` is used to call the Ollama HTTP API; `pydantic` is used for Schema validation.  
> Ollama itself needs to be installed separately, please download from https://ollama.ai and ensure `ollama serve` is running.

---

## Files to Create

```
AI_World/
└── modules/
    └── m2_agent/
        ├── __init__.py     ← Empty file to let Python recognize this as a package
        ├── main.py         ← External functions (module interface)
        └── llm_client.py   ← Ollama HTTP API call encapsulation
```

---

## Shared Schema (Use directly, do not modify)

> All schemas are defined in `AI_World/shared/schemas.py`.  
> In your code, always use `from shared.schemas import ...`; **do not define** the same classes yourself.

The following are schemas used by M2 for reference:

```python
# shared/schemas.py (Excerpt, see AI_World_Architecture.md for the full version)

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


class WorldEvent(BaseModel):
    id: str = Field(default_factory=gen_id)
    tick: int
    event_type: str  # "interaction" | "resource" | "conflict" | "discovery" | "death"
    description: str
    affected_agent_ids: list[str] = Field(default_factory=list)
    affected_location_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


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

```python
# modules/m2_agent/main.py

def create_agent(name: str, location_id: str, personality: AgentPersonality) -> Agent:
    """Create a new Agent and store it in the world state"""

def get_agent(agent_id: str) -> Agent:
    """Get the specified Agent"""

def agent_think(agent_id: str, context: str) -> str:
    """Call LLM, let the Agent think based on the context, and return action description text"""

def agent_act(agent_id: str) -> WorldEvent:
    """Let the Agent perform the action and return the corresponding WorldEvent"""

def update_agent_needs(agent_id: str) -> None:
    """Update the Agent's need values such as hunger and energy every tick"""

def list_agents() -> list[Agent]:
    """List all alive Agents"""
```

> **Important**: Function names, parameter types, and return types **cannot be modified**. The internal implementation can be designed freely.

---

## External Functions You Can Call

### From M1 (World State Engine)

```python
from modules.m1_world_state.main import (
    get_world_state,   # () -> WorldState: Get the complete world state
    update_agent,      # (agent: Agent) -> None: Update Agent state in the database
    add_event,         # (event: WorldEvent) -> None: Add a world event
    get_tick,          # () -> int: Get the current tick count
)
```

### From M3 (Memory System)

```python
from modules.m3_memory.main import (
    get_recent_memory, # (agent_id: str, n: int = 10) -> list[str]: Recent n memories
    save_memory,       # (agent_id: str, event: str, importance: float) -> str: Save memory
)
```

### From M5 (Rules Engine)

```python
from modules.m5_rules.main import (
    validate_action,   # (agent: Agent, action: str) -> tuple[bool, str]: Validate action validity
    check_survival,    # (agent: Agent) -> bool: Check if Agent is alive
)
```

---

## Prompt Assembly Logic (used internally in `agent_think`)

`agent_think` must assemble the Prompt according to the following template before passing it to Ollama:

```
You are {agent.name}, a character living in an AI world.
Personality: hunger={personality.hunger}, ambition={personality.ambition}, aggression={aggression}
Location: {location.name} ({location.terrain})
Resources: food={resources.food}, money={resources.money}
Memory: {recent_memories}
Current world state: {context}

Please describe in one sentence what action you are going to take now. The action must be one of the following:
- Gather food
- Rest
- Move to [Location Name]
- Talk with [Agent Name]
- Trade
- Other (please specify)
```

**Field Descriptions:**

| Field | Source |
|------|------|
| `agent.name` | `Agent.name` |
| `personality.hunger` | `Agent.personality.hunger` |
| `personality.ambition` | `Agent.personality.ambition` |
| `personality.aggression` | `Agent.personality.aggression` |
| `location.name` | Obtained from `WorldState.locations[agent.location_id].name` |
| `location.terrain` | Obtained from `WorldState.locations[agent.location_id].terrain` |
| `resources.food` | `Agent.resources.food` |
| `resources.money` | `Agent.resources.money` |
| `recent_memories` | Call `get_recent_memory(agent_id, n=5)` and join with newlines |
| `context` | Use the passed `context` parameter directly |

---

## Implementation Steps

### Step 1: Create `__init__.py`

```python
# modules/m2_agent/__init__.py
# Empty file to let Python recognize this as a package
```

---

### Step 2: Implement `llm_client.py` (Ollama HTTP API Encapsulation)

Ollama provides a local REST API, and the endpoint is `POST /api/generate`.

```python
# modules/m2_agent/llm_client.py

import json
import requests
from shared.schemas import Config  # Import Config schema


def load_config() -> Config:
    """
    Read AI_World/config.json, returning a Config object.
    config.json is generated by M0; format example:
    {
        "ollama_model": "gemma3:4b",
        "ollama_base_url": "http://localhost:11434",
        ...
    }
    """
    # TODO: Read config.json with open(), and parse with Config(**data)
    pass


def call_ollama(prompt: str, config: Config) -> str:
    """
    Call Ollama /api/generate endpoint, returning LLM-generated text.

    API Description:
    - URL: {config.ollama_base_url}/api/generate
    - Method: POST
    - Content-Type: application/json
    - Request body:
        {
            "model": "{config.ollama_model}",
            "prompt": "{prompt}",
            "stream": false
        }
    - Response body (when stream=false):
        {
            "model": "...",
            "response": "LLM-generated text",
            "done": true,
            ...
        }

    Error Handling:
    - If connection fails (requests.exceptions.ConnectionError), raise an exception indicating Ollama is not started.
    - If HTTP status != 200, raise an exception with status code.
    - If response is an empty string, raise an exception.

    :param prompt: Assembled prompt string
    :param config: Config object (including model name and base_url)
    :return: LLM-returned action description text (str)
    """
    url = f"{config.ollama_base_url}/api/generate"

    # TODO: Assemble request body
    payload = {
        # ...
    }

    # TODO: Send POST request, extract response["response"] and return
    pass
```

---

### Step 3: Implement `main.py`

```python
# modules/m2_agent/main.py

from shared.schemas import Agent, AgentPersonality, Resource, WorldEvent
from modules.m1_world_state.main import get_world_state, update_agent, add_event, get_tick
from modules.m3_memory.main import get_recent_memory, save_memory
from modules.m5_rules.main import validate_action, check_survival
from modules.m2_agent.llm_client import call_ollama, load_config

# Module level cache: stores the "last thought result" of each Agent, for agent_act to use
# key: agent_id, value: action text (str)
_last_action: dict[str, str] = {}


def create_agent(name: str, location_id: str, personality: AgentPersonality) -> Agent:
    """
    Create a new Agent and store it in the world state.

    Implementation steps:
    1. Create Agent object (id auto-generated, resources use defaults)
    2. Call M1's update_agent(agent) to store in the database
    3. Return the created Agent

    Note: location_id must be a location id that already exists in the world state.
    """
    # TODO
    pass


def get_agent(agent_id: str) -> Agent:
    """
    Get the specified Agent from the world state.

    Implementation steps:
    1. Call get_world_state() to get WorldState
    2. Get Agent from world_state.agents[agent_id]
    3. If agent_id does not exist, raise KeyError (with a clear error message)

    :raises KeyError: if agent_id does not exist in the world state
    """
    # TODO
    pass


def agent_think(agent_id: str, context: str) -> str:
    """
    Assemble Prompt, call Ollama LLM, let the Agent think and return action text.

    Implementation steps:
    1. Get Agent (call get_agent)
    2. Get WorldState, find the Location where the Agent resides
    3. Call get_recent_memory(agent_id, n=5) to get recent memories
    4. Assemble the prompt string according to the Prompt template (see "Prompt Assembly Logic" section)
    5. Call call_ollama(prompt, config) to get LLM response
    6. Store the response text in _last_action[agent_id] (for agent_act to use)
    7. Return action text

    :param agent_id: Target Agent's id
    :param context: Current world state description (provided by caller, e.g., M4)
    :return: LLM-generated action description text (non-empty string)
    """
    # TODO: Assemble prompt
    prompt_template = """You are {name}, a character living in an AI world.
Personality: hunger={hunger}, ambition={ambition}, aggression={aggression}
Location: {location_name}（{terrain}）
Resources: food={food}, money={money}
Memory: {memories}
Current world state: {context}

Please describe in one sentence what action you are going to take now. The action must be one of the following:
- Gather food
- Rest
- Move to [Location Name]
- Talk with [Agent Name]
- Trade
- Other (please specify)"""

    # TODO: Fill in prompt_template, call call_ollama, store and return result
    pass


def agent_act(agent_id: str) -> WorldEvent:
    """
    Let the Agent execute the action recorded in _last_action, update world state, and return WorldEvent.

    Implementation steps:
    1. Get _last_action[agent_id] (if not exists, call agent_think first to get action)
    2. Get Agent object
    3. Call validate_action(agent, action) to validate action validity
       - If invalid, change action to "Rest" (fallback behavior)
    4. Execute corresponding logic based on the action text (parse and branch):
       - "Gather food" → agent.resources.food += 10.0, event_type = "resource"
       - "Rest"        → agent.resources.energy = min(100.0, energy + 20.0), event_type = "resource"
       - "Move to ..." → Parse target location name, update agent.location_id, event_type = "interaction"
       - "Talk with..." → Update relationship values (relationships), event_type = "interaction"
       - "Trade"       → Simple resource exchange logic, event_type = "resource"
       - Other         → only record event, event_type = "discovery"
    5. Call check_survival(agent); if returns False, set agent.is_alive = False, and event_type = "death"
    6. Call update_agent(agent) to save back to M1
    7. Create and return WorldEvent, and call add_event(event) to write to world state
    8. Call save_memory(agent_id, event.description, importance=0.5) to store in memory

    Action text parsing rules (using str.startswith or in):
    - Contains "Gather food" → Gather food
    - Contains "Rest"        → Rest
    - Contains "Move to"     → Move (Format: "Move to {Location Name}")
    - Contains "Talk with"   → Talk (Format: "Talk with {Agent Name}")
    - Contains "Trade"       → Trade
    - Other                  → Other

    :param agent_id: Target Agent's id
    :return: WorldEvent representing this action
    """
    # TODO
    pass


def update_agent_needs(agent_id: str) -> None:
    """
    Called once per tick, simulating the increase of the Agent's natural needs.

    Implementation steps:
    1. Get Agent
    2. Update values according to the following rules:
       - hunger (personality.hunger) increase: += 0.01, max 1.0
         (representing the Agent getting hungrier, higher hunger means more urgent need)
       - energy (resources.energy) decrease: -= 2.0, min 0.0
         (representing the Agent consuming energy over time)
       - water (resources.water) decrease: -= 1.5, min 0.0
         (representing the Agent consuming water over time)
    3. Call check_survival(agent); if returns False, set agent.is_alive = False
    4. Call update_agent(agent) to save back to M1

    Note: personality.hunger is float; use min/max to limit the range between 0.0 and 1.0.

    :param agent_id: Target Agent's id
    """
    # TODO
    pass


def list_agents() -> list[Agent]:
    """
    List all alive (is_alive=True) Agents.

    Implementation steps:
    1. Call get_world_state() to get WorldState
    2. Filter Agents in world_state.agents.values() where is_alive == True
    3. Return list

    :return: List of all alive Agents
    """
    # TODO
    pass
```

---

### Step 4: Action Parsing Helper Functions (Recommended to be placed inside `main.py`)

```python
def _parse_action(action_text: str) -> str:
    """
    Parse the action text returned by the LLM, and return the action type.

    :return: "Gather food" | "Rest" | "Move" | "Talk" | "Trade" | "Other"
    """
    # TODO: Use `in` or `startswith` to determine the action type
    # Example:
    # if "Gather food" in action_text:
    #     return "Gather food"
    pass


def _find_location_by_name(location_name: str, world_state) -> str | None:
    """
    Find location_id based on location name.

    :param location_name: Location name (parsed from LLM-returned action text)
    :param world_state: Current WorldState
    :return: location_id, or None if not found
    """
    # TODO: Traverse world_state.locations to find the location with matching name
    pass
```

---

## Verification Standards (Must pass all to be considered complete)

- [ ] **`create_agent()` successfully creates an Agent**
  - Calling `create_agent("Xiaoming", "<valid_location_id>", AgentPersonality())` does not raise exceptions
  - The returned `Agent` object has `.name == "Xiaoming"`, `.is_alive == True`
  - The Agent's id can be found by calling `get_world_state().agents`

- [ ] **`get_agent()` correctly obtains the Agent**
  - Calling with a valid id returns the corresponding `Agent`
  - Calling with an invalid id raises a `KeyError`

- [ ] **`agent_think()` actually calls Ollama and returns non-empty text**
  - Requires Ollama service to be running (`ollama serve`) and the model downloaded
  - The returned string length is > 0
  - The string content contains action descriptions (containing one of "Gather", "Rest", "Move", "Talk", "Trade")
  - `_last_action[agent_id]` is correctly updated

- [ ] **`agent_act()` returns a valid `WorldEvent`**
  - The returned object type is `WorldEvent`
  - `event.event_type` is one of `"interaction"` | `"resource"` | `"conflict"` | `"discovery"` | `"death"`
  - `event.affected_agent_ids` contains the target `agent_id`
  - `event.tick` equals the return value of `get_tick()`
  - `get_world_state().events` contains this event after calling

- [ ] **`update_agent_needs()` hunger value increases after call**
  - Record `agent.personality.hunger` before calling
  - Re-obtain Agent after calling; `.personality.hunger` value increases by about 0.01
  - `agent.resources.energy` value decreases by about 2.0

- [ ] **Agent failing `check_survival` is set `is_alive=False`**
  - Manually set an Agent's `resources.food = 0`, `resources.water = 0`, `resources.energy = 0`
  - After calling `update_agent_needs(agent_id)`
  - Obtain that Agent from `get_world_state()`; `.is_alive == False`

- [ ] **`list_agents()` only returns alive Agents**
  - If an Agent has `is_alive=False`, it does not appear in the results of `list_agents()`
  - Return value type is `list[Agent]`

- [ ] **All functions have type hints**
  - Every parameter has type hints (e.g., `name: str`)
  - Every function has return type hints (e.g., `-> Agent`)
  - Running `python -m mypy modules/m2_agent/main.py --ignore-missing-imports` has no errors (warnings acceptable)

---

## Common Errors and Troubleshooting

| Issue | Possible Cause | Solution |
|------|----------|------|
| `ConnectionError` | Ollama service not started | Run `ollama serve` |
| `404 Not Found` | Model name incorrect | Confirm `ollama_model` in `config.json` matches `ollama list` output |
| `KeyError: agent_id` | Agent not created or M1 not initialized | First confirm M1 `init_world` has executed |
| `ModuleNotFoundError` | Incorrect execution directory | Must execute under the `AI_World/` directory, not inside `m2_agent/` |
| LLM-returned empty string | Model context too long or model issue | Shorten `recent_memories` count (n=3), or change model |

---

*This document is written based on `AI_World_Architecture.md` (last updated: 2026-05-25).*
*If there are changes to Schema or interfaces, `AI_World_Architecture.md` shall prevail.*
