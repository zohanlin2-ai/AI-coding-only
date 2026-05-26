"""
Ann Updater — runs git pull in repo root.
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


class Updater:
    def __init__(self, config: dict, base_dir: Path) -> None:
        self.base_dir = base_dir

    def run(self) -> bool:
        try:
            repo_root = get_git_repo_root(self.base_dir)
            if not repo_root:
                logging.error("Could not find Git repository root.")
                return False

            git_bin = find_git_executable()
            logging.info("Running git pull in %s...", repo_root)
            res = subprocess.run([git_bin, "pull"], cwd=str(repo_root), capture_output=True, text=True)
            if res.returncode != 0:
                logging.error("git pull failed:\n%s", res.stderr)
                return False

            logging.info("git pull completed successfully.")
            return True
        except Exception as e:
            logging.exception("Update failed: %s", e)
            return False
