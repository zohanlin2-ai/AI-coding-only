#!/usr/bin/env python3
"""
Ann Launcher — permanent process, NEVER auto-updated.

Starts current/assistant.py as a subprocess and handles lifecycle events.

Exit codes from assistant.py:
  0  — normal exit  → stop launcher completely
  42 — update requested → run updater, then restart
  other — error → log and restart
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
ASSISTANT = BASE_DIR / "current" / "assistant.py"
EXIT_UPDATE = 42
EXIT_RESTART = 3


def setup_logging() -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"launcher_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def run_assistant() -> int:
    """Launch assistant.py as a child process and return its exit code."""
    proc = subprocess.Popen([sys.executable, str(ASSISTANT)] + sys.argv[1:])
    proc.wait()
    return proc.returncode


def do_rollback(old_version: str) -> bool:
    """Load config and run rollback. Returns True on success."""
    import yaml

    config_path = BASE_DIR / "config.yml"
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        sys.path.insert(0, str(BASE_DIR))
        from updater import Updater  # noqa: PLC0415

        return Updater(config, BASE_DIR).rollback(old_version)
    except Exception as e:
        logging.exception("Failed to run rollback: %s", e)
        return False


def do_update() -> bool:
    """Load config and run the updater. Returns True on success."""
    import yaml

    config_path = BASE_DIR / "config.yml"
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        sys.path.insert(0, str(BASE_DIR))
        from updater import Updater  # noqa: PLC0415

        return Updater(config, BASE_DIR).run()
    except Exception as e:
        logging.exception("Failed to run updater: %s", e)
        return False


def main() -> None:
    setup_logging()
    
    version_file = BASE_DIR / "version.txt"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "unknown"
    logging.info("=== Ann Launcher started (v%s) ===", version)

    backoff = 1
    just_updated = False
    old_version_for_rollback = None

    while True:
        logging.info("Starting assistant...")
        start_time = time.time()
        code = run_assistant()
        elapsed = time.time() - start_time

        if code == EXIT_UPDATE:
            backoff = 1  # reset backoff on intentional restart
            logging.info("Update requested. Running updater...")
            
            # Read old version before we run updater so we can roll back if needed
            old_version_for_rollback = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "unknown"
            
            success = do_update()
            if success:
                logging.info("Update succeeded.")
                just_updated = True
            else:
                logging.info("Update FAILED — keeping current version")
                just_updated = False
        elif code == EXIT_RESTART:
            backoff = 1  # reset backoff on intentional restart
            logging.info("Restart requested by assistant. Restarting immediately...")
            just_updated = False
        elif code == 0:
            logging.info("Assistant exited cleanly. Stopping launcher.")
            sys.exit(0)
        else:
            # It crashed!
            if just_updated and old_version_for_rollback and elapsed < 10:
                logging.error(
                    "Assistant crashed on startup after update (exit code %d, ran for %.1fs). Initiating rollback...",
                    code, elapsed
                )
                rollback_success = do_rollback(old_version_for_rollback)
                if rollback_success:
                    logging.info("Rollback succeeded. Restarting with previous version...")
                else:
                    logging.error("Rollback FAILED. Cannot restore previous version.")
                just_updated = False  # prevent infinite rollback loop
                backoff = 1
            else:
                logging.warning(
                    "Assistant exited with unexpected code %d. Restarting in %ds...",
                    code, backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                just_updated = False


if __name__ == "__main__":
    main()
