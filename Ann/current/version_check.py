"""
Version check helper — called by assistant.py on startup.

Checks for updates by querying the GitHub commits API via HTTP.
"""
from __future__ import annotations

import logging
from pathlib import Path
import requests


def check_for_update(config: dict, base_dir: Path) -> str | None:
    """Return the new version string (YYYYMMDD-sha) if an update is available, else None."""
    if not config.get("update", {}).get("check_on_startup", True):
        return None

    gh = config.get("github", {})
    owner = gh.get("owner")
    repo = gh.get("repo")
    token = gh.get("token", "")

    if not owner or not repo:
        logging.warning("GitHub owner or repo config missing. Skipping update check.")
        return None

    version_file = base_dir / "version.txt"

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Try main, fallback to master
    for branch in ["main", "master"]:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            commit_data = resp.json()
            sha = commit_data.get("sha", "")
            commit_date = commit_data.get("commit", {}).get("committer", {}).get("date", "")
            if sha and commit_date:
                # Format date_part (YYYY-MM-DD -> YYYYMMDD)
                date_part = commit_date.split("T")[0].replace("-", "")
                short_sha = sha[:7]
                latest = f"{date_part}-{short_sha}"

                if not version_file.exists():
                    # First run: version.txt not yet created — treat as uninitialized,
                    # force an update so the file gets written after a successful install.
                    logging.info("version.txt not found. Triggering first-run update to %s", latest)
                    return latest

                try:
                    current = version_file.read_text(encoding="utf-8-sig").strip()
                except Exception as e:
                    logging.warning("Failed to read version.txt: %s. Forcing update.", e)
                    return latest

                if latest != current:
                    logging.info("New version available: %s (current: %s)", latest, current)
                    return latest
                return None
        except requests.exceptions.ConnectionError:
            logging.warning("No network — skipping update check.")
            return None
        except Exception as e:
            logging.debug("Update check failed for branch %s: %s", branch, e)
            continue

    logging.warning("Update check failed for both main and master branches.")
    return None
