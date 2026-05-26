# Module M3: Memory System

## Your Task

Use ChromaDB to provide vector semantic memory storage and search functions for each Agent, enabling Agents to "remember things that happened in the past" and search historical events by semantic similarity; meanwhile, maintain a global world event vector database for cross-module queries.

---

## Scope of Responsibility

- **Responsible for:**
  - Start local ChromaDB, persisting data in `data/chroma/`
  - Create and maintain an independent memory collection for each Agent (`agent_{agent_id}_memory`)
  - Maintain a global world event collection (`world_history`)
  - Implement memory storage (with `importance` weights written into metadata)
  - Implement semantic similarity search (`recall_memory`, `search_history`)
  - Implement retrieving recent memories in reverse chronological order (`get_recent_memory`)

- **Not responsible for:**
  - Agent behavioral decisions or thinking (handled by M2)
  - SQLite storage of the world state (handled by M1)
  - tick advancement and time management (handled by M6)
  - LLM calls (M3 does not use LLM)
  - Reading system settings other than `config.json`

---

## Dependencies

- **Prerequisites:**
  - M0 (Generates `config.json`, from which M3 reads basic configurations)

- **Used by the following modules:**
  - M2 (Saves memory after Agent actions, recalls memory during thinking)
  - M4 (Queries relevant memories during Multi-Agent interaction)
  - M6 (Saves world events to the vector database)
  - M8 (Integration Testing)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m3_memory\
```

All code is written in `main.py` under this directory.  
ChromaDB data is stored in `data/chroma/` at the project root directory (created by this module).

---

## Environment Setup

Run at the project root directory:

```bash
pip install chromadb pydantic
```

> **Note:** Please use `chromadb` version `>=0.4.0`. If you encounter a `sqlite3` version conflict (which occurs in some Python 3.11 environments), please use instead:
> ```bash
> pip install chromadb>=0.5.0
> ```

---

## Files to Create

```
AI_World/
├── data/
│   └── chroma/                  ← Automatically created by ChromaDB, no manual creation needed
├── modules/
│   └── m3_memory/
│       └── main.py              ← The only file to create for this module
└── shared/
    └── schemas.py               ← Already exists, import directly, do not modify
```

---

## Shared Schema (Use directly, do not modify)

Import the following classes from `shared/schemas.py`. **Do not redefine these classes in `main.py`.**

```python
# shared/schemas.py (Excerpt of M3-related parts)

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())[:8]


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

The following five functions are the **public contract** of M3 to other modules. Function names, parameter names, parameter types, and return types **must not be changed**.

```python
def save_memory(agent_id: str, event: str, importance: float) -> str:
    """
    Store a single memory of an Agent.
    - agent_id: The unique identifier of the Agent
    - event: The text description of the memory content
    - importance: Memory importance, range 0.0 (not important) ~ 1.0 (extremely important)
    - Returns: The unique id of the newly created memory (string)
    """

def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Query by semantic similarity, returning a list of the Agent's most relevant memories.
    - agent_id: The unique identifier of the Agent
    - query: The query text (semantic similarity search)
    - top_k: Maximum number of memories to return
    - Returns: List of memory content strings (most relevant first)
    """

def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """
    Return the Agent's recent n memories in reverse chronological order.
    - agent_id: The unique identifier of the Agent
    - n: Maximum number of memories to return
    - Returns: List of memory content strings (newest first)
    """

def save_world_event(event: WorldEvent) -> None:
    """
    Store a WorldEvent in the global vector database (world_history collection).
    - event: WorldEvent object
    - No return value
    """

def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """
    Semantically search world historical events.
    - query: Query text
    - top_k: Maximum number of events to return
    - Returns: List of WorldEvent objects (most relevant first)
    """
```

---

## External Functions You Can Call

M3 **does not need to call functions from other modules**. M3 is a passively called service module that only reads `config.json` and does not actively depend on functions from M1 / M2 / M4 / M6.

The way to read configuration is as follows:

```python
import json
from pathlib import Path
from shared.schemas import Config

def _load_config() -> Config:
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return Config(**json.load(f))
```

> `config.json` is located in the project root directory (`AI_World/config.json`) and is generated by M0.

---

## Implementation Steps

### Step 1: Set Directories and Imports

At the top of `modules/m3_memory/main.py`, configure `sys.path` to let Python correctly import `shared.schemas`, and initialize the ChromaDB client.

```python
# modules/m3_memory/main.py

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# Ensure shared/schemas.py can be imported
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from chromadb.config import Settings
from shared.schemas import WorldEvent, Config

# ── ChromaDB Initialization ──
CHROMA_DATA_PATH = PROJECT_ROOT / "data" / "chroma"
CHROMA_DATA_PATH.mkdir(parents=True, exist_ok=True)

# Use PersistentClient to persist data storage in data/chroma/
_client = chromadb.PersistentClient(path=str(CHROMA_DATA_PATH))
```

---

### Step 2: Get or Create Agent Memory Collection

Each Agent has its own independent collection named `agent_{agent_id}_memory`. Use `get_or_create_collection` to ensure idempotency (repeated calls will not fail).

```python
def _get_agent_collection(agent_id: str):
    """
    Get or create the memory collection for the specified Agent.
    Collection naming convention: agent_{agent_id}_memory
    """
    collection_name = f"agent_{agent_id}_memory"
    # TODO: Use _client.get_or_create_collection() to create the collection
    # Hint: collection_name can only contain alphanumeric characters, underscores, hyphens, and its length must be 3~63.
    #       If agent_id contains special characters, sanitize it first (replace with underscores).
    raise NotImplementedError
```

> **Note:** ChromaDB collection names only allow alphanumeric characters, underscores, and hyphens, and the length must be between 3 and 63. If `agent_id` might contain special characters, you need to sanitize it first:
> ```python
> import re
> safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
> collection_name = f"agent_{safe_id}_memory"
> ```

---

### Step 3: Get or Create Global World History Collection

```python
def _get_world_collection():
    """
    Get or create the collection for global world events.
    Collection name is fixed to: world_history
    """
    # TODO: Use _client.get_or_create_collection("world_history")
    raise NotImplementedError
```

---

### Step 4: Implement `save_memory`

Store a single Agent memory in the corresponding collection. Store `importance`, `tick`, `agent_id`, and `timestamp` in the metadata for subsequent filtering.

```python
def save_memory(agent_id: str, event: str, importance: float) -> str:
    """
    Store a single memory of the Agent, returning the memory id.
    """
    collection = _get_agent_collection(agent_id)
    memory_id = str(uuid.uuid4())[:8]

    # TODO: Use collection.add() to store memory
    # documents: [event]  ← Text content, ChromaDB will automatically vectorize it
    # ids: [memory_id]
    # metadatas: [{
    #     "tick": ...,        ← Current tick, 0 if not obtainable
    #     "agent_id": agent_id,
    #     "importance": importance,
    #     "timestamp": datetime.now().isoformat()
    # }]
    #
    # Hint: tick can be retrieved from M1 if possible, but since M3 does not depend on M1,
    #       a default value is acceptable (0 or passed by the caller).
    #       This version sorts by timestamp first, tick can remain 0.

    raise NotImplementedError

    return memory_id
```

---

### Step 5: Implement `recall_memory`

Use ChromaDB's semantic search to find the most relevant memories based on the `query` text.

```python
def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Semantically search the Agent's memories, returning a list of the most relevant memory texts.
    """
    collection = _get_agent_collection(agent_id)

    # TODO: Use collection.query() for semantic search
    # query_texts: [query]
    # n_results: top_k
    #
    # Note: If the number of memories in the collection is less than top_k,
    #       ChromaDB may error or return fewer results; handle the boundary case:
    #       n_results = min(top_k, collection.count())
    #       If count() == 0, return [] directly
    #
    # Return value structure: results["documents"][0] is a list of strings

    raise NotImplementedError
```

---

### Step 6: Implement `get_recent_memory`

Return the Agent's recent n memories (sorted in descending order by `timestamp` metadata).

```python
def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """
    Return the Agent's recent n memories (newest first).
    """
    collection = _get_agent_collection(agent_id)

    # TODO: Use collection.get() to retrieve all memories
    # include=["documents", "metadatas"]
    #
    # After retrieving, sort by the "timestamp" field in metadatas in descending order:
    # sorted(..., key=lambda x: x["timestamp"], reverse=True)
    #
    # Only return the first n document texts
    #
    # If collection is empty, return []

    raise NotImplementedError
```

---

### Step 7: Implement `save_world_event`

Store the `WorldEvent` object in the `world_history` collection. Put the primary fields of `WorldEvent` in the metadata during storage so that `search_history` can reconstruct it back into a `WorldEvent` object.

```python
def save_world_event(event: WorldEvent) -> None:
    """
    Store the world event in the global vector database.
    """
    collection = _get_world_collection()

    # TODO: Use collection.add() to store the event
    # documents: [event.description]  ← Use description for semantic indexing
    # ids: [event.id]
    # metadatas: [{
    #     "tick": event.tick,
    #     "event_type": event.event_type,
    #     "description": event.description,
    #     "affected_agent_ids": json.dumps(event.affected_agent_ids),
    #     "affected_location_ids": json.dumps(event.affected_location_ids),
    #     "timestamp": event.timestamp.isoformat()
    # }]
    #
    # Note: ChromaDB metadata values can only be str / int / float / bool;
    #       lists must be converted to strings using json.dumps() first.

    raise NotImplementedError
```

---

### Step 8: Implement `search_history`

Semantically search world history, reconstructing metadata back into a list of `WorldEvent` objects.

```python
def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """
    Semantically search world historical events, returning a list of WorldEvents.
    """
    collection = _get_world_collection()

    # TODO: Use collection.query() for semantic search
    # query_texts: [query]
    # n_results: min(top_k, collection.count())
    # include=["metadatas"]
    #
    # Get the list of metadatas from results["metadatas"][0]
    # Reconstruct each metadata back into a WorldEvent object:
    # WorldEvent(
    #     id=meta["id"],            ← Needs to be retrieved from ids, or stored separately in metadata
    #     tick=meta["tick"],
    #     event_type=meta["event_type"],
    #     description=meta["description"],
    #     affected_agent_ids=json.loads(meta["affected_agent_ids"]),
    #     affected_location_ids=json.loads(meta["affected_location_ids"]),
    #     timestamp=datetime.fromisoformat(meta["timestamp"])
    # )
    #
    # If collection is empty, return []
    #
    # Hint: If id is needed, you can add include=["metadatas", "documents"] in query()
    #       and store "id": event.id in metadata during save_world_event.

    raise NotImplementedError
```

> **Important Hint:** ChromaDB's `query()` does not return `ids` by default. If you need `id` to reconstruct `WorldEvent`, there are two ways:
> 1. Store `"id": event.id` additionally in the metadata of `save_world_event` (**Recommended**)
> 2. Add `include=["ids", "metadatas"]` in `query()`

---

### Step 9: Module Self-Test Script (Optional, but highly recommended)

Add the `if __name__ == "__main__":` block at the very bottom of `main.py` for easy independent execution and verification:

```python
if __name__ == "__main__":
    import time

    print("=== M3 Memory System Self-Test ===\n")

    # Test 1: save_memory + recall_memory
    print("[1] Testing save_memory...")
    mid = save_memory("agent_001", "I discovered a mysterious cave in the forest", importance=0.9)
    print(f"    Saved memory id: {mid}")

    save_memory("agent_001", "I exchanged food with agent_002", importance=0.6)
    save_memory("agent_001", "The weather is nice today, and I am resting on the plains", importance=0.2)

    print("\n[2] Testing recall_memory (Semantic query: Cave exploration)...")
    results = recall_memory("agent_001", "Exploring underground space", top_k=3)
    for i, r in enumerate(results):
        print(f"    [{i+1}] {r}")

    # Test 2: Agent Isolation
    print("\n[3] Testing Agent Memory Isolation...")
    save_memory("agent_002", "I am agent_002, and I live in the mountains", importance=0.5)
    results_002 = recall_memory("agent_002", "cave", top_k=5)
    print(f"    agent_002 query result for \"cave\" (should be empty or contain agent_002's memory only):")
    for r in results_002:
        print(f"    - {r}")

    # Test 3: get_recent_memory
    print("\n[4] Testing get_recent_memory...")
    recent = get_recent_memory("agent_001", n=2)
    print(f"    Recent 2 memories: {recent}")

    # Test 4: save_world_event + search_history
    print("\n[5] Testing save_world_event + search_history...")
    event = WorldEvent(
        tick=42,
        event_type="conflict",
        description="Two tribes clashed on the northern plains over control of water resources",
        affected_agent_ids=["agent_001", "agent_002"],
        affected_location_ids=["loc_001"]
    )
    save_world_event(event)

    search_results = search_history("Water resource clash", top_k=5)
    print(f"    Search results ({len(search_results)} items):")
    for e in search_results:
        print(f"    - [tick {e.tick}] {e.event_type}: {e.description}")

    print("\n✅ All tests passed!")
```

---

## ChromaDB Data Schema Description

### Agent Memory Collection

| Field | Description |
|------|------|
| `id` | Memory unique id (8-character UUID snippet) |
| `documents` | Memory text content (for semantic search) |
| `metadatas.tick` | Tick count at storage (int) |
| `metadatas.agent_id` | Belonging Agent id (str) |
| `metadatas.importance` | Importance weight 0.0~1.0 (float) |
| `metadatas.timestamp` | ISO format time string (str) |

### World History Collection (`world_history`)

| Field | Description |
|------|------|
| `id` | WorldEvent.id |
| `documents` | WorldEvent.description (for semantic search) |
| `metadatas.id` | WorldEvent.id (for reconstruction) |
| `metadatas.tick` | Event occurrence tick (int) |
| `metadatas.event_type` | Event type (str) |
| `metadatas.description` | Event description (str) |
| `metadatas.affected_agent_ids` | JSON string, e.g., `'["a1","a2"]'` |
| `metadatas.affected_location_ids` | JSON string, e.g., `'["loc1"]'` |
| `metadatas.timestamp` | ISO format time string (str) |

---

## FAQ and Warnings

> [!WARNING]
> **ChromaDB Collection Name Restrictions**  
> Collection names can only contain alphanumeric characters, underscores (`_`), and hyphens (`-`), with lengths between 3 and 63 characters. If `agent_id` contains special characters, sanitize it first.

> [!WARNING]
> **`n_results` Cannot Exceed Actual Item Count**  
> When calling `collection.query()`, `n_results` cannot be greater than the number of items in the collection, otherwise an exception will be raised. Always use `collection.count()` to verify the count first:
> ```python
> count = collection.count()
> if count == 0:
>     return []
> n_results = min(top_k, count)
> ```

> [!NOTE]
> **ChromaDB Default Embedding Model**  
> `chromadb` defaults to using `all-MiniLM-L6-v2` (which requires network download). If the environment cannot connect to the internet, you can use:
> ```python
> from chromadb.utils import embedding_functions
> ef = embedding_functions.DefaultEmbeddingFunction()
> collection = _client.get_or_create_collection("...", embedding_function=ef)
> ```
> Or when completely offline, switch to `OllamaEmbeddingFunction` (requires Ollama to be running locally):
> ```python
> ef = embedding_functions.OllamaEmbeddingFunction(
>     url="http://localhost:11434/api/embeddings",
>     model_name="nomic-embed-text"
> )
> ```

> [!NOTE]
> **PersistentClient vs HttpClient**  
> M3 uses `chromadb.PersistentClient` (local file storage), **no need** to start a separate ChromaDB server process. Data is written directly to the `data/chroma/` directory. This reflects the Local First design principle.

> [!TIP]
> **Application of `importance` in Search (Advanced)**  
> ChromaDB's `query()` returns results accompanied by `distances` (distance score). If you want to include `importance` for weighted re-ranking, you can compute it yourself after retrieving the results:
> ```python
> # Weighted score = (1 - distance) * importance
> # smaller distance = more similar
> ```
> Basic implementation can ignore the impact of importance on search ranking for now, and simply record it in the metadata.

---

## Verification Standards (Must pass all to be considered complete)

- [ ] `pip install chromadb pydantic` installs without errors
- [ ] Running `python modules/m3_memory/main.py` self-test script passes completely without Exceptions
- [ ] `data/chroma/` directory is automatically created and ChromaDB data is written into it (directory is not empty)
- [ ] `save_memory("agent_001", "I discovered a cave in the forest", 0.9)` returns a non-empty string id
- [ ] `recall_memory("agent_001", "underground space exploration", top_k=3)` semantically searches and finds memories related to "cave" (no exact match needed, semantic similarity is sufficient)
- [ ] Memories of different Agents are isolated from each other: Agent A's memories **will not** appear in the results of Agent B's `recall_memory`
- [ ] `get_recent_memory("agent_001", n=2)` returns a list of length ≤ 2, with the newest memories sorted first
- [ ] `save_world_event(event)` does not raise exceptions, and corresponding data is stored in `data/chroma/`
- [ ] `search_history("water resource dispute", top_k=5)` returns `list[WorldEvent]`, and each element can normally access fields like `.tick`, `.event_type`, `.description`, `.affected_agent_ids`
- [ ] Repeated startup (running `main.py` multiple times) does not error because collections already exist (`get_or_create_collection` is idempotent)
- [ ] All function type signatures strictly match the "Provided Functions" section (verify with `inspect.signature()`)

---

*Document Version: 1.0 | Corresponding to Architecture.md last updated: 2026-05-25*
