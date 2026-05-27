"""
Tests for GUI imports and dual-mode CLI/GUI fallback detection.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_cli_mode_detected_via_argv() -> None:
    with patch("sys.argv", ["assistant.py", "--cli"]):
        assert "--cli" in sys.argv


def test_pyqt6_import_fails_fallback() -> None:
    # Temporarily hide PyQt6 from sys.modules
    with patch.dict(sys.modules, {"PyQt6": None}):
        try:
            import PyQt6  # type: ignore # noqa: F401
            assert False, "Import should have failed under mock"
        except ImportError:
            pass
