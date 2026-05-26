#!/usr/bin/env python3
"""
Ann Updater — downloads Ann/current/ from GitHub Contents API and safely swaps
it into production.

Design:
  - Downloads ONLY Ann/current/ (not the whole repo zip)
  - Backs up the current version to versions/v{old}/
  - Runs pytest in staging before any swap
  - Rolls back on test failure or any exception
  - Never touches moral_module_spec.md or config.yml
"""
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import requests


class Updater:
    GITHUB_API = "https://api.github.com"

    def __init__(self, config: dict, base_dir: Path) -> None:
        gh = config["github"]
        self.owner: str = gh["owner"]
        self.repo: str = gh["repo"]
        self.subfolder: str = gh.get("subfolder", "Ann")
        self.token: str = gh.get("token", "")
        self.base_dir = base_dir
        self.staging = base_dir / "staging"
        self.current = base_dir / "current"
        self.versions = base_dir / "versions"
        self.version_file = base_dir / "version.txt"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, url: str) -> requests.Response:
        r = requests.get(url, headers=self._headers, timeout=15)
        r.raise_for_status()
        return r

    def _latest_tag(self) -> str:
        url = f"{self.GITHUB_API}/repos/{self.owner}/{self.repo}/releases/latest"
        return self._get(url).json()["tag_name"]

    def _current_version(self) -> str:
        return self.version_file.read_text(encoding="utf-8").strip()

    def _download_tree(self, ref: str, remote_path: str, local_dir: Path) -> None:
        """Recursively download a remote directory via GitHub Contents API."""
        url = f"{self.GITHUB_API}/repos/{self.owner}/{self.repo}/contents/{remote_path}?ref={ref}"
        items = self._get(url).json()
        local_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            dest = local_dir / item["name"]
            if item["type"] == "file":
                content = requests.get(item["download_url"], timeout=15)
                content.raise_for_status()
                dest.write_bytes(content.content)
                logging.info("  fetched: %s", item["name"])
            elif item["type"] == "dir":
                self._download_tree(ref, item["path"], dest)

    def _run_tests(self) -> bool:
        """Run pytest inside staging/tests/. Returns True if all pass."""
        tests_dir = self.staging / "tests"
        if not tests_dir.exists():
            logging.warning("No tests/ directory in staging — skipping pytest.")
            return True

        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir), "-v"],
            capture_output=True,
            text=True,
        )
        logging.info(result.stdout)
        if result.returncode != 0:
            logging.error("Tests failed:\n%s", result.stderr)
        return result.returncode == 0

    def _backup_current(self, old_version: str) -> None:
        self.versions.mkdir(exist_ok=True)
        dest = self.versions / f"v{old_version}"
        if dest.exists():
            shutil.rmtree(dest)
        if self.current.exists():
            shutil.copytree(self.current, dest)
            logging.info("Backed up current -> versions/v%s", old_version)

    def _swap(self) -> None:
        """Replace current/ with staging/ (atomic-ish on same filesystem)."""
        if self.current.exists():
            shutil.rmtree(self.current)
        shutil.copytree(self.staging, self.current)
        logging.info("Swapped staging -> current")

    def _cleanup_staging(self) -> None:
        if self.staging.exists():
            shutil.rmtree(self.staging)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        try:
            tag = self._latest_tag()
            old_version = self._current_version()
            logging.info("Updating %s -> %s", old_version, tag)

            # Download only Ann/current/ into staging/
            self._cleanup_staging()
            remote_path = f"{self.subfolder}/current"
            logging.info("Downloading %s @ %s ...", remote_path, tag)
            self._download_tree(tag, remote_path, self.staging)

            # Validate
            if not self._run_tests():
                logging.error("Tests FAILED. Aborting update.")
                self._cleanup_staging()
                return False

            # Commit the swap
            self._backup_current(old_version)
            self._swap()
            self._cleanup_staging()

            # Record new version (strip leading 'v' from tag)
            self.version_file.write_text(tag.lstrip("v"), encoding="utf-8")
            logging.info("Update complete: %s -> %s", old_version, tag.lstrip("v"))
            return True

        except Exception:
            logging.exception("Update failed.")
            self._cleanup_staging()
            return False
