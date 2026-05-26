# modules/m6_time_history/main.py
"""
M6 — Time & History System
Responsible for: advancing world time, reading/writing history snapshots, and querying timeline/historical events.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure importing shared and modules
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import WorldState, WorldEvent

from modules.m1_world_state.main import get_world_state, get_tick, save_state
from modules.m3_memory.main import save_world_event

# ── Constants ──
SEASONS = ["spring", "summer", "autumn", "winter"]
TICKS_PER_SEASON = 30
TICKS_PER_YEAR = 120
SNAPSHOT_INTERVAL = 10
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshots"

# Initialize snapshot directory
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ── Helper Functions (Private) ──

def _calculate_season(tick: int) -> str:
    """Calculate season based on tick count"""
    season_index = (tick % TICKS_PER_YEAR) // TICKS_PER_SEASON
    return SEASONS[season_index]


def _calculate_year(tick: int) -> int:
    """Calculate year based on tick count (starts at Year 1)"""
    return (tick // TICKS_PER_YEAR) + 1


def _is_season_end(tick: int) -> bool:
    """Check if the current tick is the last tick of a season"""
    return (tick + 1) % TICKS_PER_SEASON == 0


def _get_snapshot_path(tick: int) -> Path:
    """Get snapshot file path for the specified tick"""
    return SNAPSHOT_DIR / f"snapshot_{tick}.json"


# ── Public Functions ──

def advance_tick() -> int:
    """
    Advance world time by one tick, update season/year, and return new tick count.
    """
    current_tick = get_tick()
    new_tick = current_tick + 1

    old_season = _calculate_season(current_tick)
    new_season = _calculate_season(new_tick)
    new_year = _calculate_year(new_tick)

    # 1. Update SQLite world_meta
    from modules.m1_world_state import database as db
    db.upsert_world_meta(new_tick, new_year, new_season)

    # 2. Spawn WorldEvent on season change
    if new_season != old_season:
        desc = f"Season changed to {new_season}, current year is {new_year}."
        if new_season == "winter":
            desc += " Winter is here. All agents' food decay is increased by 20%."
        elif new_season == "summer":
            desc += " Summer is here. All agents' water decay is increased by 20%."

        event = WorldEvent(
            tick=new_tick,
            event_type="season_change",
            description=desc,
        )
        save_world_event(event)
        
        from modules.m1_world_state.main import add_event
        add_event(event)

    # 3. Save snapshot if interval matches or season ends
    if new_tick % SNAPSHOT_INTERVAL == 0 or _is_season_end(new_tick):
        save_snapshot()

    # 4. Save global JSON state snapshot
    save_state()

    return new_tick


def save_snapshot() -> None:
    """
    Save the current world state as a JSON snapshot to data/snapshots/snapshot_{tick}.json.
    """
    world_state = get_world_state()
    tick = world_state.tick
    path = _get_snapshot_path(tick)

    json_str = world_state.model_dump_json(indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json_str)


def get_snapshot(tick: int) -> Optional[WorldState]:
    """
    Read snapshot at the specified tick, return None if not found.
    """
    path = _get_snapshot_path(tick)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return WorldState.model_validate_json(content)


def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """
    Get all world events within the start_tick to end_tick (inclusive) range.
    """
    world_state = get_world_state()
    filtered = [
        event for event in world_state.events
        if start_tick <= event.tick <= end_tick
    ]
    return sorted(filtered, key=lambda e: e.tick)


def get_timeline() -> list[dict]:
    """
    Return a list of all major events for the timeline [{tick, event_type, description}].
    """
    world_state = get_world_state()
    MAJOR_EVENT_TYPES = {"season_change", "conflict", "death", "discovery"}

    timeline = []
    for event in sorted(world_state.events, key=lambda e: e.tick):
        if event.event_type in MAJOR_EVENT_TYPES:
            timeline.append({
                "tick": event.tick,
                "event_type": event.event_type,
                "description": event.description,
            })

    return timeline


def get_current_season() -> str:
    """
    Return current season string.
    """
    tick = get_tick()
    return _calculate_season(tick)
