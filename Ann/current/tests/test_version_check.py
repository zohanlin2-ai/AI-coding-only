"""
Tests for version_check helper.

Uses unittest.mock to avoid real git/network calls.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from version_check import check_for_update


@pytest.fixture
def config() -> dict:
    return {
        "github": {
            "owner": "zohanlin2-ai",
            "repo": "AI-coding-only",
            "subfolder": "Ann",
            "token": "",
        },
        "update": {"check_on_startup": True},
    }


# Mock helper
def _mock_subprocess_run(local_sha: str, remote_sha: str, remote_date: str) -> MagicMock:
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        cmd_str = " ".join(cmd)
        if "fetch" in cmd_str:
            m.stdout = ""
        elif "rev-parse" in cmd_str and "HEAD" in cmd_str:
            m.stdout = local_sha + "\n"
        elif "rev-parse" in cmd_str and "origin/main" in cmd_str:
            m.stdout = remote_sha + "\n"
        elif "rev-parse" in cmd_str and "origin/master" in cmd_str:
            m.returncode = 1
        elif "log" in cmd_str and "origin/main" in cmd_str:
            m.stdout = remote_date + "\n"
        else:
            m.returncode = 1
            m.stdout = ""
        return m
    return MagicMock(side_effect=side_effect)


def test_no_update_when_same_version(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260526-ea029a2", encoding="utf-8")

    # Mock git repository root detection
    with patch("version_check.get_git_repo_root", return_value=tmp_path):
        mock_run = _mock_subprocess_run(
            local_sha="ea029a2f524c6fe94be6ca365a7b273269ddfcc7",
            remote_sha="ea029a2f524c6fe94be6ca365a7b273269ddfcc7",
            remote_date="20260526"
        )
        with patch("version_check.subprocess.run", mock_run):
            result = check_for_update(config, tmp_path)

    assert result is None


def test_returns_new_version_when_newer(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    with patch("version_check.get_git_repo_root", return_value=tmp_path):
        mock_run = _mock_subprocess_run(
            local_sha="218ebb9b27d410bbd2f08e335a5d29e93e36c3a0",
            remote_sha="ea029a2f524c6fe94be6ca365a7b273269ddfcc7",
            remote_date="20260526"
        )
        with patch("version_check.subprocess.run", mock_run):
            result = check_for_update(config, tmp_path)

    assert result == "20260526-ea029a2"


def test_returns_none_on_exception(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    with patch("version_check.get_git_repo_root", return_value=tmp_path):
        with patch("version_check.subprocess.run", side_effect=RuntimeError("git failed")):
            result = check_for_update(config, tmp_path)

    assert result is None


def test_skips_check_when_disabled(tmp_path: Path, config: dict) -> None:
    config["update"]["check_on_startup"] = False
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    with patch("version_check.get_git_repo_root") as mock_root:
        result = check_for_update(config, tmp_path)

    mock_root.assert_not_called()
    assert result is None
