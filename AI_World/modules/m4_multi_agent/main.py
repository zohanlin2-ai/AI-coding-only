# modules/m4_multi_agent/main.py
"""
M4 — Multi-Agent Interaction Engine
Responsible for coordinating multi-agent interactions and driving the Tick loop.
"""

import sys
from pathlib import Path

# Ensure importing shared and modules
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def _safe_add_event(event: WorldEvent) -> None:
    """Safely insert event, skip if ID already exists to avoid SQLite UNIQUE constraint conflicts"""
    state = get_world_state()
    if not any(e.id == event.id for e in state.events):
        add_event(event)


def get_nearby_agents(agent_id: str, radius: int = 1) -> list[Agent]:
    """Return all alive agents within radius grids of the specified agent"""
    world: WorldState = get_world_state()

    target_agent = world.agents.get(agent_id)
    if target_agent is None or not target_agent.is_alive:
        return []

    target_location = world.locations.get(target_agent.location_id)
    if target_location is None:
        return []

    nearby: list[Agent] = []

    for other_id, other_agent in world.agents.items():
        if other_id == agent_id or not other_agent.is_alive:
            continue

        other_location = world.locations.get(other_agent.location_id)
        if other_location is None:
            continue

        distance = max(
            abs(target_location.x - other_location.x),
            abs(target_location.y - other_location.y),
        )

        if distance <= radius:
            nearby.append(other_agent)

    return nearby


def run_agent_interaction(agent_id_1: str, agent_id_2: str) -> WorldEvent:
    """Drive interaction between two agents and return the interaction event"""
    world: WorldState = get_world_state()
    current_tick: int = get_tick()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent does not exist: {agent_id_1} or {agent_id_2}")

    context_1 = f"You met {agent2.name}, think about how to respond."
    context_2 = f"You met {agent1.name}, think about how to respond."

    thought_1 = agent_think(agent_id_1, context_1)
    thought_2 = agent_think(agent_id_2, context_2)

    is_conflict = (
        agent1.personality.aggression > 0.7
        or agent2.personality.aggression > 0.7
    )
    event_type = "conflict" if is_conflict else "interaction"

    description = (
        f"{agent1.name} and {agent2.name} had a {'conflict' if is_conflict else 'interaction'}."
        f" ({agent1.name}: {thought_1[:50]}...)"
        f" ({agent2.name}: {thought_2[:50]}...)"
    )
    event = WorldEvent(
        tick=current_tick,
        event_type=event_type,
        description=description,
        affected_agent_ids=[agent_id_1, agent_id_2],
    )

    importance = 0.8 if is_conflict else 0.5
    save_memory(agent_id_1, description, importance)
    save_memory(agent_id_2, description, importance)

    _safe_add_event(event)

    return event


def negotiate(agent_id_1: str, agent_id_2: str, topic: str) -> dict:
    """Drive negotiation between two agents on a topic and return result {success: bool, outcome: str}"""
    world: WorldState = get_world_state()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent does not exist: {agent_id_1} or {agent_id_2}")

    context = f"You are negotiating with the other party about: {topic}. Express your stance."
    thought_1 = agent_think(agent_id_1, context)
    thought_2 = agent_think(agent_id_2, context)

    success_prob = (
        (agent1.personality.loyalty + agent2.personality.loyalty) / 2
        - (agent1.personality.aggression + agent2.personality.aggression) / 4
    )
    success = success_prob > 0.5

    if success:
        current_rel_1_to_2 = agent1.relationships.get(agent_id_2, 0.0)
        current_rel_2_to_1 = agent2.relationships.get(agent_id_1, 0.0)

        agent1.relationships[agent_id_2] = min(1.0, current_rel_1_to_2 + 0.1)
        agent2.relationships[agent_id_1] = min(1.0, current_rel_2_to_1 + 0.1)

        update_agent(agent1)
        update_agent(agent2)

    outcome = (
        f"Negotiation {'succeeded' if success else 'failed'} (probability: {success_prob:.2f})."
        f" Topic: {topic}."
        f" {agent1.name}'s stance: {thought_1[:50]}..."
        f" {agent2.name}'s stance: {thought_2[:50]}..."
    )

    importance = 0.7 if success else 0.4
    save_memory(agent_id_1, outcome, importance)
    save_memory(agent_id_2, outcome, importance)

    return {"success": success, "outcome": outcome}


def run_tick() -> list[WorldEvent]:
    """Execute a complete tick (all agents act sequentially) and return all events in this tick"""
    tick_events: list[WorldEvent] = []
    current_tick: int = get_tick()

    # --- Step 1: Get current world state ---
    world: WorldState = get_world_state()

    # --- Step: 2 Apply resource natural decay ---
    world = apply_resource_decay(world)

    # --- Step 3: Run action loop for each alive agent ---
    agents: list[Agent] = list_agents()  # Only returns alive agents

    for agent in agents:
        # --- 3a: Update agent needs ---
        update_agent_needs(agent.id)

        # --- Retrieve refreshed agent state ---
        refreshed_world = get_world_state()
        agent = refreshed_world.agents.get(agent.id)
        if agent is None:
            continue

        # --- 3b: Survival check ---
        is_alive = check_survival(agent)
        if not is_alive or not agent.is_alive:
            if agent.is_alive:
                agent.is_alive = False
                update_agent(agent)

            # Avoid writing duplicate death events in the same tick
            state = get_world_state()
            existing_death_event = None
            for ev in reversed(state.events):
                if ev.tick == current_tick and ev.event_type == "death" and agent.id in ev.affected_agent_ids:
                    existing_death_event = ev
                    break

            if existing_death_event:
                tick_events.append(existing_death_event)
            else:
                death_event = WorldEvent(
                    tick=current_tick,
                    event_type="death",
                    description=f"{agent.name} died due to resource exhaustion.",
                    affected_agent_ids=[agent.id],
                    affected_location_ids=[agent.location_id],
                )
                _safe_add_event(death_event)
                tick_events.append(death_event)
            continue

        # --- 3c: Find nearby agents ---
        nearby: list[Agent] = get_nearby_agents(agent.id, radius=1)

        # --- 3d: Interact with a nearby agent if present ---
        if nearby:
            interaction_target = nearby[0]
            try:
                # Initiate interaction only when agent.id < target.id to avoid duplicate double-way interactions
                if agent.id < interaction_target.id:
                    interaction_event = run_agent_interaction(agent.id, interaction_target.id)
                    tick_events.append(interaction_event)
            except Exception as e:
                print(f"[M4] Interaction failed: {agent.name} <-> {interaction_target.name}: {e}")

        # --- 3e: Make agent act ---
        try:
            action_event: WorldEvent = agent_act(agent.id)
        except Exception as e:
            print(f"[M4] agent_act failed ({agent.name}): {e}")
            continue

        # --- 3f: Validate action validity ---
        if action_event.event_type == "death":
            tick_events.append(action_event)
            continue

        is_valid, reason = validate_action(agent, action_event.event_type)
        if not is_valid:
            print(f"[M4] Action invalid ({agent.name}): {reason}, skipping.")
            continue

        _safe_add_event(action_event)
        tick_events.append(action_event)

        # --- 3g: Save memory ---
        memory_text = f"Tick {current_tick}: {action_event.description}"
        save_memory(agent.id, memory_text, importance=0.5)

    return tick_events
