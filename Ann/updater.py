"""
Ann Updater — downloads Ann/current/ from GitHub Contents API and safely swaps
it into production.
"""
from __future__ import annotations

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

    def _latest_commit_version(self) -> tuple[str, str]:
        """Returns a tuple of (ref/branch, version_string) based on commit date + sha."""
        for branch in ["main", "master"]:
            url = f"{self.GITHUB_API}/repos/{self.owner}/{self.repo}/commits/{branch}"
            try:
                resp = self._get(url)
                commit_data = resp.json()
                sha = commit_data.get("sha", "")
                commit_date = commit_data.get("commit", {}).get("committer", {}).get("date", "")
                if sha and commit_date:
                    date_part = commit_date.split("T")[0].replace("-", "")
                    short_sha = sha[:7]
                    version = f"{date_part}-{short_sha}"
                    return branch, version
            except Exception:
                continue
        raise ValueError("Could not fetch latest commit from main or master branch.")

    def _current_version(self) -> str:
        """Return local version string, or empty string if version.txt doesn't exist yet."""
        if not self.version_file.exists():
            return ""
        return self.version_file.read_text(encoding="utf-8-sig").strip()

    def _download_tree(self, ref: str, remote_path: str, local_dir: Path) -> None:
        """Recursively download a remote directory via GitHub Contents API."""
        url = f"{self.GITHUB_API}/repos/{self.owner}/{self.repo}/contents/{remote_path}?ref={ref}"
        items = self._get(url).json()
        local_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            dest = local_dir / item["name"]
            if item["type"] == "file":
                content = requests.get(item["download_url"], headers=self._headers, timeout=15)
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
        if result.returncode != 0:
            logging.error("Tests failed! pytest stdout:\n%s", result.stdout)
            logging.error("Tests failed! pytest stderr:\n%s", result.stderr)
        else:
            logging.info(result.stdout)
        return result.returncode == 0

    def _backup_current(self, old_version: str) -> None:
        self.versions.mkdir(exist_ok=True)
        label = old_version if old_version else "unknown"
        dest = self.versions / f"v{label}"
        if dest.exists():
            shutil.rmtree(dest)
        if self.current.exists():
            shutil.copytree(self.current, dest)
            logging.info("Backed up current -> versions/v%s", label)

    def _swap(self) -> None:
        """Replace current/ with staging/ (atomic-ish on same filesystem)."""
        if self.current.exists():
            shutil.rmtree(self.current)
        shutil.copytree(self.staging, self.current)
        logging.info("Swapped staging -> current")

    def _cleanup_staging(self) -> None:
        if self.staging.exists():
            shutil.rmtree(self.staging)

    def _run_self_test(self) -> bool:
        """Run self-test on the newly swapped current/assistant.py."""
        assistant_path = self.current / "assistant.py"
        if not assistant_path.exists():
            logging.error("assistant.py not found in current/ after swap.")
            return False

        try:
            args = [sys.executable, str(assistant_path), "--self-test"]
            if "--cli" in sys.argv:
                args.append("--cli")

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logging.error("Self-test process returned non-zero code %d", result.returncode)
                logging.error("Self-test stdout:\n%s", result.stdout)
                logging.error("Self-test stderr:\n%s", result.stderr)
                return False

            logging.info("Self-test passed successfully on new version.")
            return True
        except Exception as e:
            logging.exception("Exception occurred during self-test: %s", e)
            return False

    def rollback(self, old_version: str) -> bool:
        """Roll back current/ directory to a previously backed up version."""
        if not old_version:
            logging.error("Rollback failed: No old version string provided.")
            return False

        backup_dir = self.versions / f"v{old_version}"
        if not backup_dir.exists():
            logging.error("Rollback failed: Backup directory %s does not exist.", backup_dir)
            return False

        try:
            logging.info("Initiating rollback to version %s...", old_version)
            if self.current.exists():
                shutil.rmtree(self.current)
            shutil.copytree(backup_dir, self.current)
            self.version_file.write_text(old_version, encoding="utf-8")
            logging.info("Rollback to version %s complete.", old_version)
            return True
        except Exception as e:
            logging.exception("Rollback failed with exception: %s", e)
            return False

    def run(self) -> bool:
        try:
            ref, version = self._latest_commit_version()
            old_version = self._current_version()
            if old_version:
                logging.info("Updating %s -> %s", old_version, version)
            else:
                logging.info("First run — no version.txt found. Installing %s", version)

            if old_version == version:
                logging.info("Already at the latest version %s. No update needed.", version)
                return True

            # Download only Ann/current/ into staging/
            self._cleanup_staging()
            remote_path = f"{self.subfolder}/current"
            logging.info("Downloading %s @ %s ...", remote_path, ref)
            self._download_tree(ref, remote_path, self.staging)

            # Validate
            if not self._run_tests():
                logging.error("Tests FAILED. Aborting update.")
                self._cleanup_staging()
                return False

            # Commit the swap
            self._backup_current(old_version)
            self._swap()

            # Post-swap self-test
            if not self._run_self_test():
                logging.error("Self-test FAILED after swap. Initiating rollback...")
                self.rollback(old_version)
                self._cleanup_staging()
                return False

            self._cleanup_staging()

            # Record new version
            self.version_file.write_text(version, encoding="utf-8")
            logging.info("Update complete: %s -> %s", old_version, version)
            return True

        except Exception:
            logging.exception("Update failed.")
            self._cleanup_staging()
            return False
