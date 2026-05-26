# start.py — AI World One-Click Startup Script
"""
AI World One-Click Startup Script
Run command: py -3.13 start.py
"""

import sys
import os
import time
import signal
import json

# Ensure running in the AI_World/ root directory
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def check_config():
    """Verify config.json exists"""
    config_path = os.path.join(ROOT, 'config.json')
    if not os.path.exists(config_path):
        print('[!!] Cannot find config.json!')
        print('     Please execute M0 setup first:')
        print('     py -3.13 modules/m0_setup/main.py')
        sys.exit(1)
    print('[OK] config.json exists')


def run_health_check():
    """Run health check, warn if any module is abnormal"""
    from modules.m8_integration.main import health_check
    results = health_check()
    failed = [k for k, v in results.items() if v != 'ok']
    if failed:
        print(f'[!!] The following modules failed health check: {failed}')
        ans = input('     Do you still want to continue startup? [y/N] ').strip().lower()
        if ans != 'y':
            print('     Startup cancelled.')
            sys.exit(1)
    else:
        print('[OK] All modules passed health check')


def graceful_shutdown(signum, frame):
    """Safely stop on Ctrl+C"""
    print('\n\nShutdown signal received, safely shutting down AI World...')
    try:
        from modules.m8_integration.main import stop_world
        stop_world()
    except Exception as e:
        print(f'Warning: Error occurred during shutdown - {e}')
    sys.exit(0)


def main():
    print('╔══════════════════════════════════════╗')
    print('║       AI World  System Startup        ║')
    print('╚══════════════════════════════════════╝\n')

    # 1. Check config.json
    check_config()

    # 2. Health check
    print('\n[Pre-flight] Executing module health checks...')
    run_health_check()

    # 3. Start world
    print('\n[Startup] Initializing AI World...\n')
    from modules.m8_integration.main import start_world, stop_world
    signal.signal(signal.SIGINT, graceful_shutdown)
    start_world()

    # 4. Enter tick loop
    print('AI World is running. Press Ctrl+C to safely shutdown.\n')
    print('Streamlit visualization interface: http://localhost:8501\n')

    from modules.m4_multi_agent.main import run_tick
    from modules.m6_time_history.main import advance_tick, save_snapshot
    from shared.schemas import Config

    with open(os.path.join(ROOT, 'config.json'), 'r') as f:
        config = Config(**json.load(f))

    tick_count = 0
    while True:
        tick_count += 1
        print(f'─── Tick {tick_count} {"─" * 40}')

        try:
            events = run_tick()
            print(f'    {len(events)} events occurred in this tick')
        except Exception as e:
            print(f'    [!!] run_tick failed: {e}')

        try:
            new_tick = advance_tick()
            print(f'    Time advanced to tick {new_tick}')
        except Exception as e:
            print(f'    [!!] advance_tick failed: {e}')

        if tick_count % 10 == 0:
            try:
                save_snapshot()
                print(f'    Snapshot saved (tick {tick_count})')
            except Exception as e:
                print(f'    [!!] save_snapshot failed: {e}')

        time.sleep(config.tick_interval_sec)


if __name__ == '__main__':
    main()
