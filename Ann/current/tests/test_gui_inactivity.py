"""
Unit tests for the inactivity timer and pink reply pulsing light in Ann's PyQt6 GUI.
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Force offscreen rendering for GUI tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"

HAS_QT = False
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QTimer
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QTimer
        HAS_QT = True
    except ImportError:
        HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 is required for GUI tests")

if HAS_QT:
    app = QApplication.instance() or QApplication(sys.argv)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from assistant_gui import FloatingBubble, ChatWindow


@pytest.fixture
def mock_gui_components():
    config = {
        "llm": {"model": "test-model", "base_url": "http://localhost:11434"},
        "alarm": {"sound_path": "test.wav", "volume": 0.5}
    }
    controller = MagicMock()
    controller.alarm_manager = MagicMock()
    controller.alarm_trigger = MagicMock()
    controller.alarm_scheduler = MagicMock()

    return {
        "config": config,
        "controller": controller,
    }


def test_inactivity_timer_initialization(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    chat_win = ChatWindow(c["config"], c["controller"], bubble)

    assert chat_win.inactivity_timer is not None
    assert chat_win.inactivity_timer.isSingleShot()
    assert chat_win.inactivity_timer.interval() == 3 * 60 * 1000  # 3 minutes


def test_start_stop_timer(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    chat_win = ChatWindow(c["config"], c["controller"], bubble)

    chat_win.start_inactivity_timer()
    assert chat_win.inactivity_timer.isActive()

    chat_win.stop_inactivity_timer()
    assert not chat_win.inactivity_timer.isActive()


def test_timeout_triggers_shrink(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    chat_win = ChatWindow(c["config"], c["controller"], bubble)

    with patch.object(chat_win, 'shrink_back') as mock_shrink:
        chat_win._on_inactivity_timeout()
        assert mock_shrink.called


def test_send_message_resets_timer(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    chat_win = ChatWindow(c["config"], c["controller"], bubble)

    chat_win.input_field.setText("hello")
    # Mock Ollama call to prevent actual network calls during test
    with patch.object(chat_win, 'start_inactivity_timer') as mock_start:
        with patch('assistant_gui.ControllerWorker'):
            chat_win.send_message()
            assert mock_start.called


def test_alarm_extends_inactivity(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    chat_win = ChatWindow(c["config"], c["controller"], bubble)

    # 1. Timer inactive -> should not extend
    chat_win.extend_inactivity_if_alarm()
    assert not chat_win.inactivity_timer.isActive()

    # 2. Timer active -> should extend if remaining < 10s
    chat_win.start_inactivity_timer()
    # Mock remainingTime to return 5 seconds
    with patch.object(chat_win.inactivity_timer, 'remainingTime', return_value=5000):
        with patch.object(chat_win.inactivity_timer, 'start') as mock_timer_start:
            chat_win.extend_inactivity_if_alarm()
            mock_timer_start.assert_called_once_with(10000)


def test_pink_light_states(mock_gui_components):
    c = mock_gui_components
    bubble = FloatingBubble(c["config"], c["controller"])

    assert not bubble.new_reply_pending
    assert not bubble._pulse_timer.isActive()

    bubble.set_new_reply_pending(True)
    assert bubble.new_reply_pending
    assert bubble._pulse_timer.isActive()

    bubble.set_new_reply_pending(False)
    assert not bubble.new_reply_pending
    assert not bubble._pulse_timer.isActive()


def test_expand_clears_pink_light_and_starts_timer(mock_gui_components):
    c = mock_gui_components
    bubble = FloatingBubble(c["config"], c["controller"])

    bubble.set_new_reply_pending(True)

    with patch.object(bubble.chat_window, 'start_inactivity_timer') as mock_timer_start:
        with patch.object(bubble.chat_window, 'show') as mock_show:
            bubble.expand_to_chat()
            assert not bubble.new_reply_pending
            assert not bubble._pulse_timer.isActive()
            assert mock_timer_start.called
            assert mock_show.called
