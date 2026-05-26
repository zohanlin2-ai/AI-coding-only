# modules/m8_integration/main.py
"""
M8 — Integration & Testing
Responsible for: linking modules M0-M7, health checks, integration tests, startup, and shutdown.
"""

import sys
import os
import json
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from shared.schemas import Config, AgentPersonality, Location

_streamlit_process = None


def _load_config() -> Config:
    config_path = os.path.join(PROJECT_ROOT, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return Config(**json.load(f))


def _ensure_dirs():
    """Ensure required directories exist"""
    for d in ['data/snapshots', 'data/chroma']:
        os.makedirs(os.path.join(PROJECT_ROOT, d), exist_ok=True)


def health_check() -> dict:
    """
    Check if all modules (M1-M7) and Ollama are running normally.
    Returns status dict with values "ok" or "error".
    """
    result = {}

    # M1 — get_tick()
    try:
        from modules.m1_world_state.main import get_tick
        get_tick()
        result['m1_world_state'] = 'ok'
    except Exception:
        result['m1_world_state'] = 'error'

    # M2 — list_agents()
    try:
        from modules.m2_agent.main import list_agents
        list_agents()
        result['m2_agent'] = 'ok'
    except Exception:
        result['m2_agent'] = 'error'

    # M3 — import check (recall memory)
    try:
        from modules.m3_memory.main import recall_memory
        recall_memory('__health_check__', 'test', top_k=1)
        result['m3_memory'] = 'ok'
    except Exception:
        result['m3_memory'] = 'error'

    # M4 — get_nearby_agents
    try:
        from modules.m4_multi_agent.main import get_nearby_agents
        get_nearby_agents('__nonexistent__', radius=1)
        result['m4_multi_agent'] = 'ok'
    except Exception:
        result['m4_multi_agent'] = 'error'

    # M5 — get_rules_summary()
    try:
        from modules.m5_rules.main import get_rules_summary
        summary = get_rules_summary()
        assert isinstance(summary, dict)
        result['m5_rules'] = 'ok'
    except Exception:
        result['m5_rules'] = 'error'

    # M6 — get_current_season()
    try:
        from modules.m6_time_history.main import get_current_season
        season = get_current_season()
        assert season in ('spring', 'summer', 'autumn', 'winter')
        result['m6_time_history'] = 'ok'
    except Exception:
        result['m6_time_history'] = 'error'

    # M7 — app.py existence
    try:
        app_path = os.path.join(PROJECT_ROOT, 'modules', 'm7_visualization', 'app.py')
        assert os.path.exists(app_path), 'app.py not found'
        result['m7_visualization'] = 'ok'
    except Exception:
        result['m7_visualization'] = 'error'

    # Ollama — HTTP GET
    try:
        import requests
        config = _load_config()
        resp = requests.get(config.ollama_base_url, timeout=3)
        result['ollama'] = 'ok' if resp.status_code == 200 else 'error'
    except Exception:
        result['ollama'] = 'error'

    return result


def run_integration_tests() -> dict:
    """
    Run end-to-end integration tests (3 Agents, 5 ticks).
    Returns test result summary.
    """
    errors = []
    total_events = 0
    memories_saved = 0
    snapshots_saved = 0
    agents_alive = 0

    try:
        _ensure_dirs()
        config = _load_config()

        # Step 1: Initialize world
        from modules.m1_world_state.main import init_world, get_world_state
        locations = [
            Location(id='loc_plain',    name='TestPlain',    x=0, y=0, terrain='plains'),
            Location(id='loc_forest',   name='TestForest',   x=1, y=0, terrain='forest'),
            Location(id='loc_mountain', name='TestMountain', x=0, y=1, terrain='mountain'),
        ]
        world = init_world(locations, config)
        loc_ids = list(world.locations.keys())

        # Step 2: Spawn 3 agents with different personalities
        from modules.m2_agent.main import create_agent, update_agent_needs

        agent_a = create_agent('AgentA', loc_ids[0],
                               AgentPersonality(ambition=0.8, loyalty=0.7, aggression=0.2))
        agent_b = create_agent('AgentB', loc_ids[0],
                               AgentPersonality(aggression=0.7, loyalty=0.3, ambition=0.5))
        agent_c = create_agent('AgentC', loc_ids[1],
                               AgentPersonality(loyalty=0.9, aggression=0.1, ambition=0.4))

        agents = [agent_a, agent_b, agent_c]

        initial_food = {a.id: a.resources.food for a in agents}
        initial_water = {a.id: a.resources.water for a in agents}

        # Step 3: Run 5 ticks
        from modules.m4_multi_agent.main import run_tick
        from modules.m6_time_history.main import advance_tick, save_snapshot
        from modules.m3_memory.main import save_memory, save_world_event

        for tick_num in range(1, 6):
            events = run_tick()
            total_events += len(events)

            # Store events in ChromaDB
            for event in events:
                try:
                    save_world_event(event)
                except Exception as e:
                    errors.append(f'tick {tick_num} save_world_event failed: {e}')

            # Store agent memories
            for agent in agents:
                try:
                    mem_id = save_memory(
                        agent.id,
                        f'tick {tick_num} complete, {len(events)} events occurred',
                        importance=0.5,
                    )
                    if mem_id:
                        memories_saved += 1
                except Exception as e:
                    errors.append(f'tick {tick_num} save_memory({agent.name}) failed: {e}')

            # Update needs
            for agent in agents:
                try:
                    update_agent_needs(agent.id)
                except Exception as e:
                    errors.append(f'tick {tick_num} update_agent_needs({agent.name}) failed: {e}')

            # Advance time & snapshot
            advance_tick()
            try:
                save_snapshot()
                snapshots_saved += 1
            except Exception as e:
                errors.append(f'tick {tick_num} save_snapshot failed: {e}')

        # Step 4: Verify results
        world_final = get_world_state()
        agents_alive = sum(1 for a in world_final.agents.values() if a.is_alive)

        # Verification 1: At least 5 events occurred
        if total_events < 5:
            errors.append(f'Verification failed: total_events={total_events}, expected >= 5')

        # Verification 2: Resources decayed
        for agent in agents:
            af = world_final.agents.get(agent.id)
            if af is None:
                errors.append(f'Verification failed: {agent.name} does not exist in final world')
                continue
            if af.resources.food >= initial_food[agent.id] and af.resources.water >= initial_water[agent.id]:
                errors.append(f'Verification failed: {agent.name} food/water did not decay')

        # Verification 3: Memories saved
        if memories_saved == 0:
            errors.append('Verification failed: memories_saved = 0, ChromaDB contains no memory')

        # Verification 4: Snapshots saved
        if snapshots_saved == 0:
            errors.append('Verification failed: snapshots_saved = 0, no snapshots stored')

    except Exception as e:
        errors.append(f'Integration test encountered a critical error: {e}')
        agents_alive = 0

    return {
        'total_ticks': 5,
        'total_events': total_events,
        'agents_alive': agents_alive,
        'memories_saved': memories_saved,
        'snapshots_saved': snapshots_saved,
        'passed': len(errors) == 0,
        'errors': errors,
    }


def start_world() -> None:
    """
    Start all modules in order (M1→M5→M3→M2→M4→M6→M7).
    """
    global _streamlit_process

    print('=== AI World Starting ===')
    _ensure_dirs()
    config = _load_config()

    # [1] M1 Initialize World
    print('[1/7] M1: Initializing world state...')
    from modules.m1_world_state.main import init_world
    locations = [
        Location(name='Magic Village', x=0, y=0, terrain='plains'),
        Location(name='Ancient Ruins', x=1, y=0, terrain='mountain'),
        Location(name='Magic Forest', x=0, y=1, terrain='forest'),
        Location(name='Mana Spring', x=1, y=1, terrain='water'),
    ]
    world = init_world(locations, config)
    print(f'    World initialization complete, locations={len(world.locations)}')

    # [2] M5 Verify Rules Engine
    print('[2/7] M5: Loading rules engine...')
    from modules.m5_rules.main import get_rules_summary
    rules = get_rules_summary()
    print(f'    Rules load complete, rule categories={len(rules)}')

    # [3] M3 Verify Memory System
    print('[3/7] M3: Starting memory system...')
    from modules.m3_memory.main import save_memory
    save_memory('__system__', 'AI World system started', 0.1)
    print('    Memory system OK')

    # [4] M2 Spawn Initial Agents
    print(f'[4/7] M2: Spawning {config.recommended_max_agents} initial Agents...')
    from modules.m2_agent.main import create_agent
    import random
    loc_ids = list(world.locations.keys())
    personalities = [
        AgentPersonality(ambition=0.8, loyalty=0.6, aggression=0.2),
        AgentPersonality(aggression=0.7, loyalty=0.3, ambition=0.5),
        AgentPersonality(loyalty=0.9, aggression=0.1, ambition=0.4),
        AgentPersonality(hunger=0.5, fear=0.4, ambition=0.7, loyalty=0.5, aggression=0.4),
        AgentPersonality(loyalty=0.7, aggression=0.3, ambition=0.6),
    ]
    for i in range(config.recommended_max_agents):
        p = personalities[i % len(personalities)]
        create_agent(f'Agent_{i+1:02d}', random.choice(loc_ids), p)
    print(f'    {config.recommended_max_agents} Agents spawned')

    # [5] M4 Verify Interaction Mechanism
    print('[5/7] M4: Verifying multi-agent interaction mechanism...')
    from modules.m4_multi_agent.main import run_tick  # noqa: F401
    print('    M4 ready')

    # [6] M6 Start Time Management
    print('[6/7] M6: Starting time management...')
    from modules.m6_time_history.main import get_current_season
    season = get_current_season()
    print(f'    Current season: {season}')

    # [7] M7 Start Streamlit in background
    print('[7/7] M7: Starting Streamlit visualization in background...')
    app_path = os.path.join(PROJECT_ROOT, 'modules', 'm7_visualization', 'app.py')
    _streamlit_process = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', app_path,
         '--server.port=8501', '--server.headless=true'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=PROJECT_ROOT,
    )
    print(f'    Streamlit running in background (PID: {_streamlit_process.pid})')
    print('    Open in browser: http://localhost:8501')

    print('\n=== AI World Start Complete ===\n')


def stop_world() -> None:
    """
    Safely stop all modules and terminate the background Streamlit process.
    """
    global _streamlit_process

    print('=== AI World Shutting Down ===')

    try:
        from modules.m1_world_state.main import save_state
        save_state()
        print('    World state saved')
    except Exception as e:
        print(f'    Warning: World state save failed - {e}')

    try:
        from modules.m6_time_history.main import save_snapshot
        save_snapshot()
        print('    Final snapshot saved')
    except Exception as e:
        print(f'    Warning: Snapshot save failed - {e}')

    if _streamlit_process is not None:
        _streamlit_process.terminate()
        _streamlit_process = None
        print('    Streamlit stopped')

    print('=== AI World safely stopped ===')
