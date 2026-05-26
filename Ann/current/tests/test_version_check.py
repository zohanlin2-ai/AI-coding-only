"""
Tests for version_check helper.

Uses unittest.mock to avoid real network calls.
"""
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


def _mock_response(tag: str) -> MagicMock:
    m = MagicMock()
    m.json.return_value = {"tag_name": tag}
    m.raise_for_status = lambda: None
    return m


# ---------------------------------------------------------------------------
# No update when versions match
# ---------------------------------------------------------------------------


def test_no_update_when_same_version(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("1.0.0", encoding="utf-8")

    with patch("version_check.requests.get", return_value=_mock_response("v1.0.0")):
        result = check_for_update(config, tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# Returns new tag when remote is newer
# ---------------------------------------------------------------------------


def test_returns_new_tag_when_newer(tmp_path: Path, config: dict) -> None:
    (tmp_path / "version.txt").write_text("0.9.0", encoding="utf-8")

    with patch("version_check.requests.get", return_value=_mock_response("v1.0.0")):
        result = check_for_update(config, tmp_path)

    assert result == "1.0.0"


# ---------------------------------------------------------------------------
# Graceful fallback when offline
# ---------------------------------------------------------------------------


def test_returns_none_on_connection_error(tmp_path: Path, config: dict) -> None:
    import requests as req

    (tmp_path / "version.txt").write_text("0.9.0", encoding="utf-8")

    with patch("version_check.requests.get", side_effect=req.exceptions.ConnectionError):
        result = check_for_update(config, tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# Skipped when check_on_startup is false
# ---------------------------------------------------------------------------


def test_skips_check_when_disabled(tmp_path: Path, config: dict) -> None:
    config["update"]["check_on_startup"] = False
    (tmp_path / "version.txt").write_text("0.9.0", encoding="utf-8")

    with patch("version_check.requests.get") as mock_get:
        result = check_for_update(config, tmp_path)

    mock_get.assert_not_called()
    assert result is None
