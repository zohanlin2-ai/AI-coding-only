"""
Version check helper — called by assistant.py on startup.

Checks for updates by running git fetch and comparing local and remote commit SHAs.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path


def find_git_executable() -> str:
    git_path = shutil.which("git")
    if git_path:
        return git_path
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


def check_for_update(config: dict, base_dir: Path) -> str | None:
    """Return the new version string (YYYYMMDD-sha) if an update is available, else None."""
    if not config.get("update", {}).get("check_on_startup", True):
        return None

    repo_root = get_git_repo_root(base_dir)
    if not repo_root:
        logging.warning("Not inside a Git repository. Skipping update check.")
        return None

    git_bin = find_git_executable()

    try:
        # Run git fetch to update remote tracking branch information
        subprocess.run(
            [git_bin, "fetch", "origin"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        # Get local commit SHA
        local_sha = subprocess.run(
            [git_bin, "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Get remote commit SHA (try main, fallback to master)
        remote_sha = None
        branch = None
        for b in ["main", "master"]:
            res = subprocess.run(
                [git_bin, "rev-parse", f"origin/{b}"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                remote_sha = res.stdout.strip()
                branch = b
                break

        if not remote_sha:
            logging.warning("Could not find origin/main or origin/master tracking branch.")
            return None

        if local_sha != remote_sha:
            # Get remote commit date for formatting YYYYMMDD-sha
            date_res = subprocess.run(
                [
                    git_bin,
                    "log",
                    "-1",
                    "--format=%cd",
                    "--date=format:%Y%m%d",
                    f"origin/{branch}",
                ],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True,
            )
            date_str = date_res.stdout.strip()
            latest = f"{date_str}-{remote_sha[:7]}"

            current = (base_dir / "version.txt").read_text(encoding="utf-8").strip()
            if latest != current:
                logging.info("New git commit available: %s (current: %s)", latest, current)
                return latest

        return None

    except Exception as e:
        logging.warning("Git update check failed: %s", e)
        return None
