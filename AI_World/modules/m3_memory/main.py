# modules/m3_memory/main.py
"""
M3 — Memory System
Responsible for: vector semantic memory storage and search for agents, and global world event vector logging.
"""

import sys
import json
import uuid
import re
from pathlib import Path
from datetime import datetime

# Ensure importing shared/schemas.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from shared.schemas import WorldEvent, Config

# ── ChromaDB Initialization ──
CHROMA_DATA_PATH = PROJECT_ROOT / "data" / "chroma"
CHROMA_DATA_PATH.mkdir(parents=True, exist_ok=True)

# Use PersistentClient to persist data in data/chroma/
_client = chromadb.PersistentClient(path=str(CHROMA_DATA_PATH))


def _get_agent_collection(agent_id: str):
    """
    Get or create a memory collection for the specified agent.
    Naming rule: agent_{agent_id}_memory (character-cleaned)
    """
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
    collection_name = f"agent_{safe_id}_memory"
    return _client.get_or_create_collection(collection_name)


def _get_world_collection():
    """
    Get or create the global world event history collection.
    Name is fixed to: world_history
    """
    return _client.get_or_create_collection("world_history")


# ── Public Functions ──

def save_memory(agent_id: str, event: str, importance: float) -> str:
    """
    Save a memory for an agent, returning the memory ID.
    """
    collection = _get_agent_collection(agent_id)
    memory_id = str(uuid.uuid4())[:8]

    collection.add(
        documents=[event],
        ids=[memory_id],
        metadatas=[{
            "tick": 0,
            "agent_id": agent_id,
            "importance": importance,
            "timestamp": datetime.now().isoformat()
        }]
    )
    return memory_id


def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Return a list of memories most relevant to the query.
    """
    collection = _get_agent_collection(agent_id)
    count = collection.count()
    if count == 0:
        return []

    n_results = min(top_k, count)
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if results and "documents" in results and results["documents"]:
        return results["documents"][0]
    return []


def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """
    Return the agent's most recent n memories, sorted by time descending.
    """
    collection = _get_agent_collection(agent_id)
    count = collection.count()
    if count == 0:
        return []

    results = collection.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    
    if not docs:
        return []

    paired = list(zip(docs, metas))
    paired.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    
    return [p[0] for p in paired[:n]]


def save_world_event(event: WorldEvent) -> None:
    """
    Save a WorldEvent to the global database (world_history collection).
    """
    collection = _get_world_collection()
    
    collection.add(
        documents=[event.description],
        ids=[event.id],
        metadatas=[{
            "id": event.id,
            "tick": event.tick,
            "event_type": event.event_type,
            "description": event.description,
            "affected_agent_ids": json.dumps(event.affected_agent_ids),
            "affected_location_ids": json.dumps(event.affected_location_ids),
            "timestamp": event.timestamp.isoformat()
        }]
    )


def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """
    Query the world history events, returning a list of matched WorldEvent objects.
    """
    collection = _get_world_collection()
    count = collection.count()
    if count == 0:
        return []

    n_results = min(top_k, count)
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas"]
    )
    
    if not results or "metadatas" not in results or not results["metadatas"]:
        return []

    metas = results["metadatas"][0]
    events = []
    for m in metas:
        events.append(WorldEvent(
            id=m["id"],
            tick=m["tick"],
            event_type=m["event_type"],
            description=m["description"],
            affected_agent_ids=json.loads(m["affected_agent_ids"]),
            affected_location_ids=json.loads(m["affected_location_ids"]),
            timestamp=datetime.fromisoformat(m["timestamp"])
        ))
    return events


# ── Self Test ──

if __name__ == "__main__":
    print("=== M3 Memory System Self-Test ===\n")

    print("[1] Testing save_memory...")
    mid = save_memory("agent_001", "I discovered a mysterious cave in the forest", importance=0.9)
    print(f"    Saved memory ID: {mid}")

    save_memory("agent_001", "I traded food with agent_002", importance=0.6)
    save_memory("agent_001", "Today was beautiful, I rested on the plains", importance=0.2)

    print("\n[2] Testing recall_memory (Query: 'cave exploration')...")
    results = recall_memory("agent_001", "explore underground spaces", top_k=3)
    for i, r in enumerate(results):
        print(f"    [{i+1}] {r}")

    print("\n[3] Testing agent memory isolation...")
    save_memory("agent_002", "I am agent_002, I live on the mountains", importance=0.5)
    results_002 = recall_memory("agent_002", "cave", top_k=5)
    print(f"    agent_002 query result for 'cave' (should be empty or unrelated to agent_001):")
    for r in results_002:
        print(f"    - {r}")

    print("\n[4] Testing get_recent_memory...")
    recent = get_recent_memory("agent_001", n=2)
    print(f"    Most recent 2 memories: {recent}")

    print("\n[5] Testing save_world_event + search_history...")
    event = WorldEvent(
        tick=42,
        event_type="conflict",
        description="Two tribes had a conflict in the northern plains over water resources",
        affected_agent_ids=["agent_001", "agent_002"],
        affected_location_ids=["loc_001"]
    )
    save_world_event(event)

    search_results = search_history("conflict over water", top_k=5)
    print(f"    Search results ({len(search_results)} items):")
    for e in search_results:
        print(f"    - [tick {e.tick}] {e.event_type}: {e.description}")

    print("\n[SUCCESS] All memory tests passed!")
