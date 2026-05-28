"""
Tests for Updater self-test and rollback.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from updater import Updater

# Skip tests in this file if the root updater.py is an older version lacking rollback/self-test support
HAS_ROLLBACK_SUPPORT = hasattr(Updater, "rollback") and hasattr(Updater, "_run_self_test")
pytestmark = pytest.mark.skipif(not HAS_ROLLBACK_SUPPORT, reason="Local updater.py is outdated and lacks rollback/self-test support")


@pytest.fixture
def config() -> dict:
    return {
        "github": {
            "owner": "zohanlin2-ai",
            "repo": "AI-coding-only",
            "subfolder": "Ann",
            "token": "",
        }
    }


def test_updater_rollback(tmp_path: Path, config: dict) -> None:
    # Set up directory structure in tmp_path
    current_dir = tmp_path / "current"
    versions_dir = tmp_path / "versions"
    version_file = tmp_path / "version.txt"

    current_dir.mkdir()
    versions_dir.mkdir()

    # Create dummy files in current/
    (current_dir / "assistant.py").write_text("print('current version')", encoding="utf-8")

    # Create backup for old version "v1.0.0"
    backup_dir = versions_dir / "v1.0.0"
    backup_dir.mkdir()
    (backup_dir / "assistant.py").write_text("print('backup version')", encoding="utf-8")

    updater = Updater(config, tmp_path)

    # Execute rollback to "1.0.0"
    success = updater.rollback("1.0.0")

    assert success is True
    assert version_file.read_text(encoding="utf-8").strip() == "1.0.0"
    assert (current_dir / "assistant.py").read_text(encoding="utf-8") == "print('backup version')"


def test_updater_rollback_non_existent(tmp_path: Path, config: dict) -> None:
    updater = Updater(config, tmp_path)
    # rollback should fail if version is empty or backup doesn't exist
    assert updater.rollback("") is False
    assert updater.rollback("1.0.0") is False


def test_updater_run_self_test_success(tmp_path: Path, config: dict) -> None:
    current_dir = tmp_path / "current"
    current_dir.mkdir()
    assistant_path = current_dir / "assistant.py"
    
    # Python script that exits cleanly (code 0)
    assistant_path.write_text("import sys\nsys.exit(0)", encoding="utf-8")

    updater = Updater(config, tmp_path)
    assert updater._run_self_test() is True


def test_updater_run_self_test_failure(tmp_path: Path, config: dict) -> None:
    current_dir = tmp_path / "current"
    current_dir.mkdir()
    assistant_path = current_dir / "assistant.py"
    
    # Python script that crashes (code 1)
    assistant_path.write_text("import sys\nsys.exit(1)", encoding="utf-8")

    updater = Updater(config, tmp_path)
    assert updater._run_self_test() is False
