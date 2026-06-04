"""
Unit tests for conversational update [UPDATE] marker handling in CLI and GUI.
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Force offscreen rendering for GUI tests to prevent crashes in headless environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Try to import Qt libraries dynamically
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

# Skip GUI-dependent tests in this file if Qt is not available
pytestmark = pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 is required for GUI tests")

if HAS_QT:
    # Ensure QApplication is initialized (needed for widget creation)
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Add parent path to import assistant_gui
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from assistant_gui import ChatWindow
    import assistant


@pytest.fixture
def mock_gui_components():
    config = {
        "llm": {"model": "test-model", "base_url": "http://localhost:11434"},
        "alarm": {"sound_path": "test.wav", "volume": 0.5}
    }
    evaluator = MagicMock()
    alarm_manager = MagicMock()
    alarm_trigger = MagicMock()
    alarm_scheduler = MagicMock()
    intent_parser = MagicMock()
    
    return {
        "config": config,
        "evaluator": evaluator,
        "alarm_manager": alarm_manager,
        "alarm_trigger": alarm_trigger,
        "alarm_scheduler": alarm_scheduler,
        "intent_parser": intent_parser
    }


def test_gui_conversational_update(mock_gui_components):
    c = mock_gui_components
    bubble = MagicMock()
    
    chat_win = ChatWindow(
        c["config"], c["evaluator"], bubble, c["alarm_manager"],
        c["alarm_trigger"], c["alarm_scheduler"], c["intent_parser"]
    )
    
    # Verify input starts enabled
    assert chat_win.send_btn.isEnabled()
    assert chat_win.input_field.isEnabled()
    
    # Mock QTimer.singleShot to spy on it
    with patch.object(QTimer, "singleShot") as mock_timer:
        # Call handle_controller_result with ControllerResult having [UPDATE] marker
        from core_controller import ControllerResult
        result = ControllerResult(reply="Updating now, goodbye!", marker="[UPDATE]")
        chat_win.handle_controller_result(result)
        
        # Verify UI controls disabled
        assert not chat_win.send_btn.isEnabled()
        assert not chat_win.input_field.isEnabled()
        assert chat_win.title_label.text() == "Updating..."
        
        # Verify timer was scheduled for update exit (EXIT_UPDATE = 42)
        assert mock_timer.call_count == 2
        
        # Check first call (scroll to bottom)
        first_args, _ = mock_timer.call_args_list[0]
        assert first_args[0] == 50
        
        # Check second call (exit code 42)
        second_args, _ = mock_timer.call_args_list[1]
        assert second_args[0] == 1500  # 1.5 seconds delay
        exit_callable = second_args[1]
        
        with patch.object(QApplication, "exit") as mock_app_exit:
            exit_callable()
            mock_app_exit.assert_called_once_with(42)


def test_cli_conversational_update():
    conversation = []
    reply = "I am updating CLI! [UPDATE]"
    
    with patch("sys.exit") as mock_exit:
        if "[UPDATE]" in reply:
            clean_reply = reply.replace("[UPDATE]", "").strip()
            conversation.append({"role": "assistant", "content": clean_reply})
            mock_exit(42)
            
        assert len(conversation) == 1
        assert conversation[0] == {"role": "assistant", "content": "I am updating CLI!"}
        mock_exit.assert_called_once_with(42)
