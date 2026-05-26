#!/usr/bin/env python3
"""
Ann Launcher ??permanent process, NEVER auto-updated.

Starts current/assistant.py as a subprocess and handles lifecycle events.

Exit codes from assistant.py:
  0  ??normal exit  ??stop launcher completely
  42 ??update requested ??run updater, then restart
  other ??error ??log and restart
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


def find_git_executable() -> str:
    import shutil
    git_path = shutil.which("git")
    if git_path:
        return git_path
    from pathlib import Path
    nrf_git = r"C:\ncs\toolchains\cf2149caf2\cmd\git.exe"
    if Path(nrf_git).exists():
        return nrf_git
    common_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]
    for p in common_paths:
        if Path(p).exists():
            return p
    return "git"


def get_git_repo_root(start_dir: Path) -> Path | None:
    for p in [start_dir] + list(start_dir.parents):
        if (p / ".git").is_dir():
            return p
    return None


def do_update() -> bool:
    """Run git pull in the repository root using a detached PowerShell script."""
    repo_root = get_git_repo_root(BASE_DIR)
    if not repo_root:
        logging.error("Could not find Git repository root.")
        return False

    git_bin = find_git_executable()
    logging.info("Scheduling Git update in repo root: %s", repo_root)

    # Detached PowerShell helper to run git pull, update version.txt, and restart launcher
    version_file = BASE_DIR / "version.txt"
    ps_command = (
        f"Start-Sleep -s 2; "
        f"cd '{repo_root}'; "
        f"& '{git_bin}' pull; "
        f"$sha = (& '{git_bin}' rev-parse --short=7 HEAD); "
        f"$date = (& '{git_bin}' log -1 --format=%cd --date=format:%Y%m%d HEAD); "
        f"\"$date-$sha\" | Out-File -FilePath '{version_file}' -Encoding utf8 -NoNewline; "
        f"cd '{BASE_DIR}'; "
        f"Start-Process py 'launcher.py'"
    )

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_command],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        logging.info("Detached PowerShell updater spawned. Exiting current launcher.")
        sys.exit(0)
    except Exception as e:
        logging.exception("Failed to spawn PowerShell updater: %s", e)
        return False


def main() -> None:
    setup_logging()
    logging.info("=== Ann Launcher started (v%s) ===", (BASE_DIR / "version.txt").read_text().strip())

    while True:
        logging.info("Starting assistant...")
        code = run_assistant()

        if code == EXIT_UPDATE:
            logging.info("Update requested. Running Git updater...")
            success = do_update()
            if not success:
                logging.info("Git update FAILED.")
        elif code == 0:
            logging.info("Assistant exited cleanly. Stopping launcher.")
            sys.exit(0)
        else:
            logging.warning("Assistant exited with unexpected code %d. Restarting...", code)


if __name__ == "__main__":
    main()

