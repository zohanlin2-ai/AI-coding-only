#!/usr/bin/env python3
"""
Ann Launcher — permanent process, NEVER auto-updated.

Starts current/assistant.py as a subprocess and handles lifecycle events.

Exit codes from assistant.py:
  0  — normal exit  → restart assistant
  42 — update requested → run updater, then restart
  other — error → log and restart
"""
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
ASSISTANT = BASE_DIR / "current" / "assistant.py"
EXIT_UPDATE = 42


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
    proc = subprocess.Popen([sys.executable, str(ASSISTANT)])
    proc.wait()
    return proc.returncode


def do_update() -> bool:
    """Load config and run the updater. Returns True on success."""
    import yaml

    config_path = BASE_DIR / "config.yml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # updater.py lives at root level — never inside current/
    sys.path.insert(0, str(BASE_DIR))
    from updater import Updater  # noqa: PLC0415

    return Updater(config, BASE_DIR).run()


def main() -> None:
    setup_logging()
    logging.info("=== Ann Launcher started (v%s) ===", (BASE_DIR / "version.txt").read_text().strip())

    while True:
        logging.info("Starting assistant...")
        code = run_assistant()

        if code == EXIT_UPDATE:
            logging.info("Update requested. Running updater...")
            success = do_update()
            logging.info("Update %s.", "succeeded" if success else "FAILED — keeping current version")
        elif code == 0:
            logging.info("Assistant exited cleanly.")
        else:
            logging.warning("Assistant exited with unexpected code %d.", code)


if __name__ == "__main__":
    main()
