# modules/m8_integration/test_integration.py
"""
M8 Integration Test Script — Standalone Execution
Run command: py -3.13 modules/m8_integration/test_integration.py
"""

import sys
import os
import json
from datetime import datetime

# Path setup: Ensure importing from root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from modules.m8_integration.main import health_check, run_integration_tests


def sep(char='─', width=60):
    print(char * width)


def run_health_check_report() -> bool:
    sep('=')
    print('  AI World Health Check')
    print(f'  Execution Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    sep('=')

    results = health_check()
    all_ok = True
    for module, status in results.items():
        icon = '[OK]' if status == 'ok' else '[!!]'
        print(f'  {icon}  {module:<25} {status}')
        if status != 'ok':
            all_ok = False

    sep()
    print(f'  Overall Status: {"ALL NORMAL" if all_ok else "Some modules failed, please resolve before continuing"}')
    sep('=')
    return all_ok


def run_integration_test_report() -> dict:
    sep('=')
    print('  AI World Integration Test (3 Agent x 5 Tick)')
    print(f'  Execution Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    sep('=')

    print('  Running integration tests, please wait (includes LLM calls)...\n')
    results = run_integration_tests()

    print(f'  Total Ticks    : {results["total_ticks"]}')
    print(f'  Total Events   : {results["total_events"]}')
    print(f'  Agents Alive   : {results["agents_alive"]}')
    print(f'  Memories Saved : {results["memories_saved"]}')
    print(f'  Snapshots Saved: {results["snapshots_saved"]}')
    sep()

    if results['passed']:
        print('  Result: Integration Test Passed [SUCCESS]')
    else:
        print('  Result: Integration Test Failed [FAILED]')
        print('  Errors List:')
        for err in results['errors']:
            print(f'    - {err}')

    sep('=')
    return results


def save_report(health_ok: bool, test_results: dict):
    report = {
        'generated_at': datetime.now().isoformat(),
        'health_check_passed': health_ok,
        'integration_test': test_results,
    }
    report_path = os.path.join(ROOT, 'data', 'integration_report.json')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f'\n  Report saved to: {report_path}')


if __name__ == '__main__':
    # 1. Health Check
    health_ok = run_health_check_report()

    if not health_ok:
        print('\n  Some modules failed health check. Fix them before running integration tests.')
        sys.exit(1)

    print()

    # 2. Integration Test
    test_results = run_integration_test_report()

    # 3. Save Report
    save_report(health_ok, test_results)

    sys.exit(0 if test_results['passed'] else 1)
