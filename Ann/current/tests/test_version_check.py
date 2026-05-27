"""
Tests for version_check helper.

Uses unittest.mock to avoid real network calls.
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


def _mock_commit_response(sha: str, date: str) -> MagicMock:
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {
        "sha": sha,
        "commit": {
            "committer": {
                "date": date
            }
        }
    }
    return m


# ---------------------------------------------------------------------------
# No update when versions match
# ---------------------------------------------------------------------------


def test_no_update_when_same_version(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260526-ea029a2", encoding="utf-8")

    mock_resp = _mock_commit_response("ea029a2f524c6fe94be6ca365a7b273269ddfcc7", "2026-05-26T08:10:34Z")
    with patch("version_check.requests.get", return_value=mock_resp):
        result = check_for_update(config, tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# Returns new tag when remote is newer
# ---------------------------------------------------------------------------


def test_returns_new_version_when_newer(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    mock_resp = _mock_commit_response("ea029a2f524c6fe94be6ca365a7b273269ddfcc7", "2026-05-26T08:10:34Z")
    with patch("version_check.requests.get", return_value=mock_resp):
        result = check_for_update(config, tmp_path)

    assert result == "20260526-ea029a2"


# ---------------------------------------------------------------------------
# Returns None on exceptions
# ---------------------------------------------------------------------------


def test_returns_none_on_exception(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    import requests
    with patch("version_check.requests.get", side_effect=requests.exceptions.RequestException("connection failed")):
        result = check_for_update(config, tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# Skips check when disabled
# ---------------------------------------------------------------------------


def test_skips_check_when_disabled(tmp_path: Path, config: dict) -> None:
    config["update"]["check_on_startup"] = False
    (tmp_path / "version.txt").write_text("20260525-218ebb9", encoding="utf-8")

    with patch("version_check.requests.get") as mock_get:
        result = check_for_update(config, tmp_path)

    mock_get.assert_not_called()
    assert result is None


# ---------------------------------------------------------------------------
# First-run bootstrap: no version.txt → force update
# ---------------------------------------------------------------------------


def test_returns_latest_when_no_version_file(tmp_path: Path, config: dict) -> None:
    """If version.txt does not exist, treat as first run and return the latest version."""
    # tmp_path has no version.txt
    mock_resp = _mock_commit_response("ea029a2f524c6fe94be6ca365a7b273269ddfcc7", "2026-05-26T08:10:34Z")
    with patch("version_check.requests.get", return_value=mock_resp):
        result = check_for_update(config, tmp_path)

    assert result == "20260526-ea029a2"

