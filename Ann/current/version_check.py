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
    """Return the new version string if an update is available, else None."""
    if not config.get("update", {}).get("check_on_startup", True):
        return None

    gh = config["github"]
    owner, repo = gh["owner"], gh["repo"]
    token = gh.get("token", "")

    current = (base_dir / "version.txt").read_text(encoding="utf-8").strip()

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for branch in ["main", "master"]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            commit_data = resp.json()
            sha = commit_data.get("sha", "")
            commit_date = commit_data.get("commit", {}).get("committer", {}).get("date", "")
            if sha and commit_date:
                date_part = commit_date.split("T")[0].replace("-", "")
                short_sha = sha[:7]
                version = f"{date_part}-{short_sha}"

                if version != current:
                    logging.info("New version available: %s (current: %s)", version, current)
                    return version
                return None
        except requests.exceptions.ConnectionError:
            logging.warning("No network — skipping update check.")
            return None
        except Exception:
            continue

    logging.warning("Update check failed for both main and master branches.")
    return None
