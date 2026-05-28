"""
Tests for conversational updates in both CLI and GUI modes.
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Force offscreen rendering for GUI tests to prevent crashes in headless environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant import EXIT_UPDATE

# Import GUI if available to test its logic
try:
    from PyQt6.QtWidgets import QApplication
    from assistant_gui import ChatWindow, UpdateCheckWorker
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from assistant_gui import ChatWindow, UpdateCheckWorker
        HAS_QT = True
    except ImportError:
        HAS_QT = False


# ---------------------------------------------------------------------------
# GUI Conversational Update Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def qapp():
    if not HAS_QT:
        pytest.skip("Qt library not available, skipping GUI tests")
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_gui_init_with_update(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    # ChatWindow initialized with new_tag
    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag="20260527-latest"
    )

    assert chat_window.awaiting_update_confirm is True
    assert chat_window.pending_version == "20260527-latest"


def test_gui_update_confirm_yes(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag="20260527-latest"
    )

    chat_window.input_field.setText("\u597d")
    with patch("assistant_gui.OllamaWorker.start") as mock_worker_start:
        chat_window.send_message()
        mock_worker_start.assert_called_once()
        assert chat_window.awaiting_update_confirm is False
        assert chat_window.pending_version is None


def test_gui_update_confirm_no(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag="20260527-latest"
    )

    chat_window.input_field.setText("\u4e0d\u8981")
    chat_window.send_message()
    assert chat_window.awaiting_update_confirm is False
    assert chat_window.pending_version is None


def test_gui_manual_update_check_no_new_version(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser
    )

    with patch("assistant_gui.UpdateCheckWorker.start") as mock_worker_start:
        chat_window.input_field.setText("\u66f4\u65b0")
        chat_window.send_message()
        mock_worker_start.assert_called_once()
        assert chat_window.title_label.text() == "Checking for updates..."


def test_gui_handle_update_check_finished_with_version(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser
    )

    chat_window.handle_update_check_finished("20260527-latest", "")
    assert chat_window.awaiting_update_confirm is True
    assert chat_window.pending_version == "20260527-latest"
    assert chat_window.title_label.text() == "Ann"


def test_gui_handle_update_check_finished_no_version(qapp) -> None:
    config = {"llm": {"model": "test-model"}}
    evaluator = MagicMock()
    bubble = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()

    chat_window = ChatWindow(
        config, evaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser
    )

    chat_window.handle_update_check_finished("", "")
    assert chat_window.awaiting_update_confirm is False
    assert chat_window.pending_version is None
    assert chat_window.title_label.text() == "Ann"
