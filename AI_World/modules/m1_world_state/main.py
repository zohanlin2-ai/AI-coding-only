import json
import sys
import os
from pathlib import Path

# Allow Python to find the shared package
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.schemas import (
    Agent, Config, Location, Organization, Resource, WorldEvent, WorldState
)
from modules.m1_world_state import database as db

# ── Module Level Cache ──
_world_state: WorldState | None = None
_config: Config | None = None


def _load_config() -> Config:
    """Read and parse config.json"""
    global _config
    config_path = ROOT_DIR / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("config.json not found, please run M0 Setup module first.")
    with open(config_path, "r", encoding="utf-8") as f:
        _config = Config(**json.load(f))
    return _config


def _get_default_locations() -> list[Location]:
    """Return 5 default magic locations"""
    return [
        Location(name="Magic Village",  x=2, y=2, terrain="plains"),
        Location(name="Mana Spring",  x=0, y=2, terrain="water"),
        Location(name="Ancient Ruins", x=4, y=4, terrain="mountain"),
        Location(name="Magic Forest",   x=1, y=3, terrain="forest"),
        Location(name="Shimmering Lake",    x=3, y=1, terrain="water"),
    ]


# ── 對外函數 ───────────────────────────────────────────────────────────

def init_world(locations: list[Location], config: Config) -> WorldState:
    """Initialize world, create database structure, and return initial WorldState.
    
    If locations is an empty list, automatically use 5 default locations.
    """
    global _world_state, _config

    _config = config
    db.create_tables()

    # Clear any existing old data to ensure clean initialization
    conn = db.get_connection()
    with conn:
        conn.execute("DELETE FROM world_meta")
        conn.execute("DELETE FROM locations")
        conn.execute("DELETE FROM agents")
        conn.execute("DELETE FROM organizations")
        conn.execute("DELETE FROM events")
    conn.close()

    if not locations:
        locations = _get_default_locations()

    for loc in locations:
        db.upsert_location(loc.model_dump())

    db.upsert_world_meta(tick=0, year=1, season="spring")

    _world_state = get_world_state()
    return _world_state


def get_world_state() -> WorldState:
    """Read the current complete world state (re-read from db to ensure latest data)"""
    global _world_state

    # 1. Get meta info
    meta = db.get_world_meta()

    # 2. 取得 locations
    loc_list = db.get_all_locations()
    locations_dict = {loc["id"]: Location(**loc) for loc in loc_list}

    # 3. 取得 agents
    agent_list = db.get_all_agents()
    agents_dict = {ag["id"]: Agent(**ag) for ag in agent_list}

    # 4. 取得 organizations
    org_list = db.get_all_organizations()
    orgs_dict = {org["id"]: Organization(**org) for org in org_list}

    # 5. 取得 events
    event_list = db.get_all_events()
    events_obj_list = [WorldEvent(**ev) for ev in event_list]

    state = WorldState(
        tick=meta["tick"],
        year=meta["year"],
        season=meta["season"],
        locations=locations_dict,
        agents=agents_dict,
        organizations=orgs_dict,
        events=events_obj_list
    )

    _world_state = state
    return state


def update_agent(agent: Agent) -> None:
    """Update a single Agent state in database"""
    global _world_state
    db.upsert_agent(agent.model_dump())
    if _world_state:
        _world_state.agents[agent.id] = agent


def update_location_resources(location_id: str, resources: Resource) -> None:
    """Update resources of the specified location"""
    global _world_state
    state = get_world_state()
    if location_id in state.locations:
        loc = state.locations[location_id]
        loc.resources = resources
        db.upsert_location(loc.model_dump())
        if _world_state:
            _world_state.locations[location_id] = loc


def add_event(event: WorldEvent) -> None:
    """Add a new world event"""
    global _world_state
    db.insert_event(event.model_dump())
    if _world_state:
        # Avoid duplicate caching
        if not any(e.id == event.id for e in _world_state.events):
            _world_state.events.append(event)


def get_tick() -> int:
    """Get the current tick count"""
    meta = db.get_world_meta()
    return meta["tick"]


def save_state() -> None:
    """Serialize current world state and save to data/world_snapshot.json"""
    state = get_world_state()
    snapshot_path = ROOT_DIR / "data" / "world_snapshot.json"
    os.makedirs(snapshot_path.parent, exist_ok=True)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(state.model_dump(mode='json'), f, ensure_ascii=False, indent=2)


def load_state() -> WorldState:
    """Read world state from data/world_snapshot.json and sync back to SQLite"""
    global _world_state
    snapshot_path = ROOT_DIR / "data" / "world_snapshot.json"
    if not snapshot_path.exists():
        raise FileNotFoundError("Snapshot file data/world_snapshot.json not found")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    state = WorldState.model_validate(data)

    # Clear SQLite database
    conn = db.get_connection()
    with conn:
        conn.execute("DELETE FROM world_meta")
        conn.execute("DELETE FROM locations")
        conn.execute("DELETE FROM agents")
        conn.execute("DELETE FROM organizations")
        conn.execute("DELETE FROM events")
    conn.close()

    # Write latest state
    db.upsert_world_meta(state.tick, state.year, state.season)
    for loc in state.locations.values():
        db.upsert_location(loc.model_dump())
    for agent in state.agents.values():
        db.upsert_agent(agent.model_dump())
    for org in state.organizations.values():
        db.upsert_organization(org.model_dump())
    for event in state.events:
        db.insert_event(event.model_dump())

    _world_state = state
    return state
