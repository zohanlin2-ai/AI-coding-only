"""
Version check helper — called by assistant.py on startup.

Returns the new tag string (e.g. "1.2.0") if a newer release exists on GitHub,
or None if up-to-date, no network, or an error occurs.
"""
from __future__ import annotations

import logging
from pathlib import Path

import requests


def check_for_update(config: dict, base_dir: Path) -> str | None:
    """Return the new version tag if an update is available, else None."""
    if not config.get("update", {}).get("check_on_startup", True):
        return None

    gh = config["github"]
    owner, repo = gh["owner"], gh["repo"]
    token = gh.get("token", "")

    current = (base_dir / "version.txt").read_text(encoding="utf-8").strip()

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        latest = resp.json().get("tag_name", "").lstrip("v")

        if latest and latest != current:
            logging.info("New version available: %s (current: %s)", latest, current)
            return latest

        return None

    except requests.exceptions.ConnectionError:
        logging.warning("No network — skipping update check.")
        return None
    except Exception as e:
        logging.warning("Update check failed: %s", e)
        return None
