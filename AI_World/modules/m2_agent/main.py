# modules/m2_agent/main.py
"""
main.py — Public interface and core logic of M2 Agent system.
"""

import sys
import os
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

# Allow importing modules and shared schemas
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import Agent, AgentPersonality, Resource, WorldEvent
from modules.m1_world_state.main import get_world_state, update_agent, add_event, get_tick
from modules.m3_memory.main import get_recent_memory, save_memory
from modules.m5_rules.main import validate_action, check_survival
from modules.m2_agent.llm_client import call_ollama, load_config

# Cache of each agent's last thought action
_last_action: dict[str, str] = {}

MALE_FIRST_NAMES = ["Gandalf", "Merlin", "Albus", "Severus", "Sirius", "Cedric", "Gellert", "Elrond", "Saruman", "Newt", "Arthur", "Remus"]
FEMALE_FIRST_NAMES = ["Hermione", "Luna", "Ginny", "Minerva", "Bellatrix", "Lily", "Narcissa", "Fleur", "Galadriel", "Arwen", "Morgana", "Sybil"]
MAGIC_TITLES = ["the Wise", "the Grey", "the Brave", "the Shadow", "Lovegood", "Black", "Potter", "Dumbledore", "Granger", "Weasley", "McGonagall", "Lestrange", "Gaunt", "Slytherin", "Gryffindor", "Ravenclaw", "Hufflepuff", "the Mage", "the Seer", "the Alchemist", "of the Forest", "of the Valley"]


def generate_magic_name_and_gender() -> tuple[str, str]:
    gender = random.choice(["male", "female"])
    first_name = random.choice(MALE_FIRST_NAMES) if gender == "male" else random.choice(FEMALE_FIRST_NAMES)
    title = random.choice(MAGIC_TITLES)
    return f"{first_name} {title}", gender


def create_agent(name: str, location_id: str, personality: AgentPersonality) -> Agent:
    """
    Create a new Agent and save to the world state.
    If name is empty or starts with 'Agent', randomly generate a magic name and gender.
    """
    state = get_world_state()
    if location_id not in state.locations:
        raise KeyError(f"Location ID '{location_id}' not found, cannot spawn Agent.")

    gender = "male"
    final_name = name
    if not name or name.startswith("Agent"):
        final_name, gender = generate_magic_name_and_gender()
    else:
        gender = random.choice(["male", "female"])

    agent = Agent(
        name=final_name,
        gender=gender,
        location_id=location_id,
        personality=personality
    )
    
    update_agent(agent)
    return agent


def get_agent(agent_id: str) -> Agent:
    """
    Retrieve specified Agent from the world state.
    """
    state = get_world_state()
    if agent_id not in state.agents:
        raise KeyError(f"Agent with ID '{agent_id}' not found in world state.")
    return state.agents[agent_id]


def agent_think(agent_id: str, context: str) -> str:
    """
    Compose Prompt, call Ollama LLM, and return the action decision.
    """
    agent = get_agent(agent_id)
    state = get_world_state()
    loc = state.locations.get(agent.location_id)

    memories_list = get_recent_memory(agent_id, n=5)
    memories_str = "\n".join(memories_list) if memories_list else "No relevant memory"

    prompt_template = """You are {name} (Gender: {gender}), a character living in a magic world.
Personality: hunger={hunger:.2f}, ambition={ambition:.2f}, aggression={aggression:.2f}
Location: {location_name} ({terrain})
Resources: Food={food:.2f}, Money={money:.2f}, Mana(MP)={mana:.2f}, Materials={materials:.2f}
Memories: {memories}
Current World Status: {context}

Please describe what action you want to take now in ONE sentence in English. Your action MUST be one of the following:
- Gather Food (Only works in Forest or Plains terrain)
- Rest (Restore energy)
- Meditate (Restore mana, format must contain "Meditate")
- Move to [Location Name]
- Talk to [Agent Name]
- Trade (Buy food/materials)
- Cast: Teleportation (Costs 30 MP, instantly teleports to any location on the map. Format must contain "Cast: Teleportation" and the destination location name)
- Cast: Healing (Costs 20 MP, quickly restores energy. Format must contain "Cast: Healing")
- Cast: Alchemy (Costs 15 MP and 10 Materials, synthesizes food or money. Format must contain "Cast: Alchemy")
- Cast: Fireball (Costs 25 MP, duels another agent at the same location. Format must contain "Cast: Fireball" and the target's name)
- Other (Please specify)"""

    prompt = prompt_template.format(
        name=agent.name,
        gender="Male" if agent.gender == "male" else "Female",
        hunger=agent.personality.hunger,
        ambition=agent.personality.ambition,
        aggression=agent.personality.aggression,
        location_name=loc.name if loc else "Unknown",
        terrain=loc.terrain if loc else "Unknown",
        food=agent.resources.food,
        money=agent.resources.money,
        mana=agent.resources.mana,
        materials=agent.resources.materials,
        memories=memories_str,
        context=context
    )

    config = load_config()
    response = call_ollama(prompt, config)
    
    _last_action[agent_id] = response
    return response


def _parse_action(action_text: str) -> str:
    """
    Parse action text and return action type.
    """
    action_text_lower = action_text.lower()
    if "cast: teleportation" in action_text_lower or "teleportation" in action_text_lower or "傳送" in action_text:
        return "Cast: Teleportation"
    elif "cast: healing" in action_text_lower or "healing" in action_text_lower or "治癒" in action_text:
        return "Cast: Healing"
    elif "cast: alchemy" in action_text_lower or "alchemy" in action_text_lower or "鍊金" in action_text:
        return "Cast: Alchemy"
    elif "cast: fireball" in action_text_lower or "fireball" in action_text_lower or "火球" in action_text:
        return "Cast: Fireball"
    elif "meditate" in action_text_lower or "冥想" in action_text:
        return "Meditate"
    elif "gather food" in action_text_lower or "採集食物" in action_text:
        return "Gather Food"
    elif "rest" in action_text_lower or "休息" in action_text:
        return "Rest"
    elif "move to" in action_text_lower or "移動" in action_text:
        return "Move"
    elif "talk to" in action_text_lower or "交談" in action_text or "speak" in action_text_lower:
        return "Talk"
    elif "trade" in action_text_lower or "交易" in action_text or "buy" in action_text_lower:
        return "Trade"
    else:
        return "Other"


def agent_act(agent_id: str) -> WorldEvent:
    """
    Perform action recorded in _last_action, update world state, and return WorldEvent.
    """
    action = _last_action.get(agent_id)
    if not action:
        action = agent_think(agent_id, "You woke up and need to decide what to do.")

    agent = get_agent(agent_id)
    state = get_world_state()

    ok, reason = validate_action(agent, action)
    if not ok:
        action = "Rest"

    action_type = _parse_action(action)
    event_type = "discovery"
    description = f"{agent.name} performed action: {action}"
    affected_agent_ids = [agent_id]
    affected_location_ids = [agent.location_id]

    if action_type == "Gather Food":
        agent.resources.food += 10.0
        event_type = "resource"
        description = f"{agent.name} gathered 10.0 units of food at the current location."
        
    elif action_type == "Rest":
        agent.resources.energy = min(100.0, agent.resources.energy + 20.0)
        event_type = "resource"
        description = f"{agent.name} rested and restored energy."

    elif action_type == "Meditate":
        agent.resources.mana = min(100.0, agent.resources.mana + 30.0)
        agent.resources.energy = max(0.0, agent.resources.energy - 5.0)
        event_type = "resource"
        description = f"{agent.name} closed their eyes to meditate, restoring 30.0 mana while consuming a bit of energy."

    elif action_type == "Cast: Teleportation":
        target_loc_id = None
        target_loc_name = ""
        for loc in state.locations.values():
            if loc.name.lower() in action.lower():
                target_loc_id = loc.id
                target_loc_name = loc.name
                break
        
        if not target_loc_id:
            other_locs = [l for l in state.locations.values() if l.id != agent.location_id]
            if other_locs:
                dest = random.choice(other_locs)
                target_loc_id = dest.id
                target_loc_name = dest.name
        
        if target_loc_id:
            agent.resources.mana = max(0.0, agent.resources.mana - 30.0)
            old_location_name = state.locations[agent.location_id].name if agent.location_id in state.locations else "Unknown"
            agent.location_id = target_loc_id
            event_type = "interaction"
            description = f"✨ {agent.name} chanted an incantation and cast [Teleportation], instantly teleporting from {old_location_name} to {target_loc_name} in a flash of blue light!"
            affected_location_ids.append(target_loc_id)
        else:
            agent.resources.mana = min(100.0, agent.resources.mana + 30.0)
            event_type = "resource"
            description = f"{agent.name} tried to cast Teleportation but the spell fizzled, meditating to recover mana instead."

    elif action_type == "Cast: Healing":
        agent.resources.mana = max(0.0, agent.resources.mana - 20.0)
        agent.resources.energy = min(100.0, agent.resources.energy + 30.0)
        event_type = "resource"
        description = f"💚 {agent.name} cast [Healing], enveloped in a soft green glow, restoring 30.0 energy!"

    elif action_type == "Cast: Alchemy":
        agent.resources.mana = max(0.0, agent.resources.mana - 15.0)
        agent.resources.materials = max(0.0, agent.resources.materials - 10.0)
        
        if "money" in action.lower() or "gold" in action.lower() or "coin" in action.lower():
            agent.resources.money += 20.0
            product = "20.0 gold coins"
        else:
            agent.resources.food += 20.0
            product = "20.0 units of food"
            
        event_type = "resource"
        description = f"🧪 {agent.name} cast [Alchemy], consuming materials and converting mana to synthesize {product}!"

    elif action_type == "Cast: Fireball":
        agent.resources.mana = max(0.0, agent.resources.mana - 25.0)
        targets = [ag for ag in state.agents.values() if ag.id != agent.id and ag.location_id == agent.location_id and ag.is_alive]
        
        if targets:
            target_agent = random.choice(targets)
            affected_agent_ids.append(target_agent.id)
            
            win_prob = 0.5 + (agent.personality.aggression - target_agent.personality.aggression) * 0.2
            win_prob = max(0.1, min(0.9, win_prob))
            
            if random.random() < win_prob:
                stolen_res = "food" if target_agent.resources.food > target_agent.resources.money else "money"
                amount = min(15.0, getattr(target_agent.resources, stolen_res))
                
                if stolen_res == "food":
                    target_agent.resources.food -= amount
                    agent.resources.food += amount
                    res_name = "food"
                else:
                    target_agent.resources.money -= amount
                    agent.resources.money += amount
                    res_name = "gold coins"
                
                update_agent(target_agent)
                event_type = "conflict"
                description = f"🔥 {agent.name} launched a [Fireball] at {target_agent.name}! The fire flared, defeating the opponent and stealing {amount:.1f} {res_name}!"
            else:
                event_type = "conflict"
                description = f"🔥 {agent.name} launched a [Fireball] at {target_agent.name}, but the opponent nimbly dodged, causing no damage!"
        else:
            event_type = "resource"
            description = f"🔥 {agent.name} launched a [Fireball] into the empty air, and it burst in the sky, leaving only a puff of smoke."
        
    elif action_type == "Move":
        target_loc_id = None
        target_loc_name = ""
        for loc in state.locations.values():
            if loc.name.lower() in action.lower():
                target_loc_id = loc.id
                target_loc_name = loc.name
                break
        
        if target_loc_id:
            old_location_name = state.locations[agent.location_id].name if agent.location_id in state.locations else "Unknown"
            agent.location_id = target_loc_id
            event_type = "interaction"
            description = f"{agent.name} moved from {old_location_name} to {target_loc_name}."
            affected_location_ids.append(target_loc_id)
            
    elif action_type == "Talk":
        target_agent_id = None
        target_agent_name = ""
        for ag in state.agents.values():
            if ag.id != agent.id and (ag.name.lower() in action.lower() or ag.id in action):
                target_agent_id = ag.id
                target_agent_name = ag.name
                break
                
        if target_agent_id:
            curr_rel = agent.relationships.get(target_agent_id, 0.0)
            agent.relationships[target_agent_id] = min(1.0, curr_rel + 0.1)
            
            target_agent = state.agents[target_agent_id]
            target_curr_rel = target_agent.relationships.get(agent.id, 0.0)
            target_agent.relationships[agent.id] = min(1.0, target_curr_rel + 0.1)
            
            update_agent(target_agent)
            event_type = "interaction"
            description = f"{agent.name} talked with {target_agent_name}, increasing their mutual relationship."
            affected_agent_ids.append(target_agent_id)
            
    elif action_type == "Trade":
        target_agent_id = None
        target_agent_name = ""
        for ag in state.agents.values():
            if ag.id != agent.id and (ag.name.lower() in action.lower() or ag.id in action):
                target_agent_id = ag.id
                target_agent_name = ag.name
                break
                
        if target_agent_id:
            target_agent = state.agents[target_agent_id]
            from modules.m5_rules.main import _parse_trade_amount
            amount = _parse_trade_amount(action)
            if amount <= 0:
                amount = 10.0
                
            fee = amount * 0.1
            required_money = amount + fee
            
            if agent.resources.money >= required_money and target_agent.resources.food >= 10.0:
                agent.resources.money -= required_money
                agent.resources.food += 10.0
                
                target_agent.resources.money += amount
                target_agent.resources.food -= 10.0
                
                update_agent(target_agent)
                event_type = "resource"
                description = f"{agent.name} traded with {target_agent_name}: {agent.name} paid {required_money:.1f} gold coins and obtained 10.0 units of food."
                affected_agent_ids.append(target_agent_id)
            else:
                agent.resources.energy = min(100.0, agent.resources.energy + 20.0)
                event_type = "resource"
                description = f"{agent.name}'s trade with {target_agent_name} failed due to insufficient resources, resting instead."
                affected_agent_ids.append(target_agent_id)

    if not check_survival(agent):
        agent.is_alive = False
        event_type = "death"
        description = f"💀 {agent.name} died in {state.locations[agent.location_id].name} due to starvation or dehydration."

    update_agent(agent)

    event = WorldEvent(
        tick=get_tick(),
        event_type=event_type,
        description=description,
        affected_agent_ids=affected_agent_ids,
        affected_location_ids=affected_location_ids
    )
    add_event(event)

    save_memory(agent_id, event.description, importance=0.5)
    return event


def update_agent_needs(agent_id: str) -> None:
    """
    Call every tick to simulate agent natural needs decay.
    """
    agent = get_agent(agent_id)

    agent.personality.hunger = min(1.0, agent.personality.hunger + 0.01)
    agent.resources.energy = max(0.0, agent.resources.energy - 2.0)
    agent.resources.water = max(0.0, agent.resources.water - 1.5)

    if not check_survival(agent):
        agent.is_alive = False
        state = get_world_state()
        loc_name = state.locations[agent.location_id].name if agent.location_id in state.locations else "Unknown Location"
        event = WorldEvent(
            tick=get_tick(),
            event_type="death",
            description=f"{agent.name} died in {loc_name} due to extremely low resources.",
            affected_agent_ids=[agent_id],
            affected_location_ids=[agent.location_id]
        )
        add_event(event)
        save_memory(agent_id, event.description, importance=0.9)

    update_agent(agent)


def list_agents() -> list[Agent]:
    """
    List all alive agents.
    """
    state = get_world_state()
    return [ag for ag in state.agents.values() if ag.is_alive]
