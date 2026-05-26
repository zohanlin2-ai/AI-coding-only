# modules/m5_rules/main.py
"""
M5 — Rules Engine
Responsible for: action validation, resource decay, survival checks, and economic rules.
"""

import sys
import os
import re

# Allow Python to find shared/ and modules/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from shared.schemas import Agent, WorldState, Resource, Location, WorldEvent
from modules.m1_world_state.main import get_world_state

# ── Constant Definitions (Centralized Rules Configuration) ──

# Resource decay rules
FOOD_DECAY_DEFAULT = 5.0       # Default tick decay
FOOD_DECAY_FOREST = 3.0        # Forest tick decay (wild food available)
WATER_DECAY = 4.0              # Default water tick decay
ENERGY_DECAY_DEFAULT = 3.0     # Default energy tick decay
ENERGY_DECAY_RESTING = 1.0     # Resting energy tick decay

# Economic rules
TRADE_FEE_RATE = 0.10          # 10% fee rate
LOCATION_RESOURCE_MAX = 1000.0 # Maximum resource capacity at any location
RESOURCE_REGEN_PER_TICK = 2.0  # Natural regen rate of location resources per tick
MONEY_MIN = 0.0                # Minimum gold balance


# ── Helper Functions (Private) ──

def _get_agent_terrain(agent: Agent, world_state: WorldState) -> str:
    """Get the terrain of the agent's current location, return 'unknown' if not found"""
    location = world_state.locations.get(agent.location_id)
    return location.terrain if location else "unknown"


def _is_agent_resting(agent: Agent, world_state: WorldState) -> bool:
    """
    Check if the agent is currently resting.
    Strategy: search for the latest event involving this agent, return True if description contains 'rest' or '休息'.
    """
    for event in reversed(world_state.events):
        if agent.id in event.affected_agent_ids:
            desc = event.description.lower()
            if "rest" in desc or "休息" in desc:
                return True
            else:
                return False
    return False


def _parse_trade_amount(action: str) -> float:
    """
    Parse the trade amount from the action string.
    E.g., "I want to trade 20 food with Merlin" -> returns 20.0
    Return 0.0 if parsing fails.
    """
    numbers = re.findall(r'\d+\.?\d*', action)
    if numbers:
        return float(numbers[0])
    return 0.0


# ── Public Functions ──

def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """
    Validate if the agent's action string is legal.
    - Return (True, "") if action is legal.
    - Return (False, "Reason description") if action is illegal.
    """
    world_state = get_world_state()

    # 1. Ensure the agent is alive
    if not agent.is_alive:
        return (False, "Dead agents cannot perform actions")

    # 2. Get current location and terrain
    current_location = world_state.locations.get(agent.location_id)
    current_terrain = current_location.terrain if current_location else "unknown"

    # Magic action validations
    action_lower = action.lower()
    if "teleport" in action_lower or "傳送" in action:
        if agent.resources.mana < 30.0:
            return (False, "Insufficient mana to cast Teleportation (requires 30 MP)")

    if "heal" in action_lower or "治癒" in action:
        if agent.resources.mana < 20.0:
            return (False, "Insufficient mana to cast Healing (requires 20 MP)")

    if "alchemy" in action_lower or "鍊金" in action:
        if agent.resources.mana < 15.0 or agent.resources.materials < 10.0:
            return (False, "Insufficient resources to cast Alchemy (requires 15 MP and 10 materials)")

    if "fireball" in action_lower or "火球" in action:
        if agent.resources.mana < 25.0:
            return (False, "Insufficient mana to cast Fireball (requires 25 MP)")

    if "meditate" in action_lower or "冥想" in action:
        if agent.resources.energy < 5.0:
            return (False, "Energy too low to focus on meditation")

    # 3. Gather Food: only allowed in forest or plains
    if "gather food" in action_lower or "採集食物" in action:
        if current_terrain not in ("forest", "plains"):
            return (False, "Gathering food is only allowed in Forest or Plains terrain")

    # 4. Move: target location must exist
    if "move" in action_lower or "移動" in action:
        target_id = None
        # Try to find matching location by split tokens
        for token in action.split():
            clean_token = "".join(c for c in token if c.isalnum() or c == "_")
            # Case insensitive check
            for loc_id, loc in world_state.locations.items():
                if clean_token.lower() == loc.name.lower() or clean_token == loc_id:
                    target_id = loc_id
                    break
            if target_id:
                break
        
        # Substring search if not found
        if not target_id:
            for loc_id, loc in world_state.locations.items():
                if loc.name.lower() in action.lower() or loc_id in action:
                    target_id = loc_id
                    break
        if not target_id:
            return (False, "Target location does not exist in the world")

    # 5. Trade: must specify a valid partner; buyer money cannot drop below minimum
    if "trade" in action_lower or "交易" in action:
        target_agent_id = None
        for ag_id, ag in world_state.agents.items():
            if ag_id != agent.id and (ag.name.lower() in action.lower() or ag_id in action):
                target_agent_id = ag_id
                break
        if not target_agent_id:
            for token in action.split():
                clean_token = "".join(c for c in token if c.isalnum() or c == "_")
                if clean_token != agent.id and clean_token in world_state.agents:
                    target_agent_id = clean_token
                    break

        if not target_agent_id:
            return (False, "Trade partner not specified")

        trade_amount = _parse_trade_amount(action)
        if trade_amount > 0:
            fee = trade_amount * TRADE_FEE_RATE
            required_money = trade_amount + fee
            if agent.resources.money < required_money:
                return (False, "Insufficient funds to trade")

    # 6. Universal rule: money cannot go below minimum
    if agent.resources.money < MONEY_MIN:
        return (False, "This action results in a negative money balance")

    return (True, "")


def apply_resource_decay(world_state: WorldState) -> WorldState:
    """
    Apply natural resource decay to all alive agents and natural regeneration to locations per tick.
    Return updated WorldState (does not save directly to db).
    """
    # 1. Apply decay to each alive Agent
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue

        location = world_state.locations.get(agent.location_id)
        terrain = location.terrain if location else "unknown"

        food_decay = FOOD_DECAY_FOREST if terrain == "forest" else FOOD_DECAY_DEFAULT
        energy_decay = ENERGY_DECAY_RESTING if _is_agent_resting(agent, world_state) else ENERGY_DECAY_DEFAULT

        # Apply decay (resources cannot fall below 0)
        agent.resources.food = max(0.0, agent.resources.food - food_decay)
        agent.resources.water = max(0.0, agent.resources.water - WATER_DECAY)
        agent.resources.energy = max(0.0, agent.resources.energy - energy_decay)

        # Apply mana regeneration (base +5.0, additional +15.0 at mana spring)
        mana_regen = 5.0
        if location and "spring" in location.name.lower():
            mana_regen += 15.0
        agent.resources.mana = min(100.0, agent.resources.mana + mana_regen)

        world_state.agents[agent_id] = agent

    # 2. Apply natural resource regeneration to each Location
    for loc_id, location in world_state.locations.items():
        location.resources.food = min(LOCATION_RESOURCE_MAX, location.resources.food + RESOURCE_REGEN_PER_TICK)
        location.resources.water = min(LOCATION_RESOURCE_MAX, location.resources.water + RESOURCE_REGEN_PER_TICK)
        location.resources.materials = min(LOCATION_RESOURCE_MAX, location.resources.materials + RESOURCE_REGEN_PER_TICK)
        world_state.locations[loc_id] = location

    return world_state


def check_survival(agent: Agent) -> bool:
    """
    Check if the agent survives.
    - If food <= 0 or water <= 0 -> returns False (dead)
    - Otherwise returns True (alive)
    """
    if agent.resources.food <= 0.0 or agent.resources.water <= 0.0:
        return False
    return True


def apply_economic_rules(world_state: WorldState) -> WorldState:
    """
    Apply economic constraints, ensuring money is non-negative and location resources do not exceed cap.
    """
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue
        agent.resources.money = max(MONEY_MIN, agent.resources.money)
        world_state.agents[agent_id] = agent

    for loc_id, location in world_state.locations.items():
        location.resources.food = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.food))
        location.resources.water = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.water))
        location.resources.energy = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.energy))
        location.resources.money = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.money))
        location.resources.materials = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.materials))
        world_state.locations[loc_id] = location

    return world_state


def get_rules_summary() -> dict:
    """
    Return rules summary dict for visualization or integration tests.
    """
    return {
        "resource_decay": {
            "food_decay_default": FOOD_DECAY_DEFAULT,
            "food_decay_forest": FOOD_DECAY_FOREST,
            "water_decay": WATER_DECAY,
            "energy_decay_default": ENERGY_DECAY_DEFAULT,
            "energy_decay_resting": ENERGY_DECAY_RESTING,
            "description": "Natural resource decay applied to alive agents per tick; forest terrain decays food slower; resting decays energy slower"
        },
        "action_rules": {
            "gather_food": "Only allowed in Forest or Plains terrain",
            "move": "Target location must exist in the world",
            "trade": "Partner must be specified and both parties must have sufficient resources",
            "universal": "No action can make money balance negative"
        },
        "economic_rules": {
            "trade_fee_rate": TRADE_FEE_RATE,
            "location_resource_max": LOCATION_RESOURCE_MAX,
            "resource_regen_per_tick": RESOURCE_REGEN_PER_TICK,
            "money_min": MONEY_MIN,
            "description": "Trading incurs 10% fee; location resources capped at 1000; natural regen +2 per tick"
        },
        "survival_rules": {
            "death_conditions": ["food <= 0", "water <= 0"],
            "description": "Agent dies if food or water decays to 0"
        }
    }
