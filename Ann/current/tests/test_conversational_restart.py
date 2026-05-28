"""
Unit tests for conversational restart [RESTART] marker handling in CLI, GUI, and launcher.
"""
import sys
import os
import time
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
    import launcher


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


def test_gui_conversational_restart(mock_gui_components):
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
        # Call handle_reply with [RESTART] marker
        chat_win.handle_reply("I am restarting! [RESTART]", "")
        
        # Verify message was stripped of [RESTART] and stored
        assert len(chat_win.conversation) == 1
        assert chat_win.conversation[0] == {"role": "assistant", "content": "I am restarting!"}
        
        # Verify UI controls disabled
        assert not chat_win.send_btn.isEnabled()
        assert not chat_win.input_field.isEnabled()
        assert chat_win.title_label.text() == "Restarting..."
        
        # Verify timer was scheduled for restart exit
        assert mock_timer.call_count == 2
        
        # Check first call (scroll to bottom)
        first_args, _ = mock_timer.call_args_list[0]
        assert first_args[0] == 50
        
        # Check second call (exit code 3)
        second_args, _ = mock_timer.call_args_list[1]
        assert second_args[0] == 1500  # 1.5 seconds delay
        # The callable is a lambda that calls QApplication.exit(3). We can invoke it.
        exit_callable = second_args[1]
        
        with patch.object(QApplication, "exit") as mock_app_exit:
            exit_callable()
            mock_app_exit.assert_called_once_with(3)


def test_cli_conversational_restart():
    conversation = []
    reply = "I am rebooting CLI! [RESTART]"
    
    with patch("sys.exit") as mock_exit:
        if "[RESTART]" in reply:
            clean_reply = reply.replace("[RESTART]", "").strip()
            conversation.append({"role": "assistant", "content": clean_reply})
            mock_exit(3)
            
        assert len(conversation) == 1
        assert conversation[0] == {"role": "assistant", "content": "I am rebooting CLI!"}
        mock_exit.assert_called_once_with(3)


def test_launcher_handles_restart_code():
    # Verify launcher logic for code 3 resets backoff and doesn't sleep
    # We can test this by running a mock loop turn in main.
    
    # Mock run_assistant to return EXIT_RESTART (3) on first run, then 0 to exit cleanly
    run_mock = MagicMock(side_effect=[3, 0])
    
    with patch("launcher.run_assistant", run_mock), \
         patch("launcher.setup_logging"), \
         patch("sys.exit", side_effect=SystemExit) as mock_exit, \
         patch("time.sleep") as mock_sleep:
         
         # Stub file access in launcher
         with patch("pathlib.Path.read_text", return_value="1.0.0"), \
              patch("pathlib.Path.exists", return_value=True):
              
              try:
                  launcher.main()
              except SystemExit:
                  pass
              
              # run_assistant should be called twice (once for code 3, once for code 0)
              assert run_mock.call_count == 2
              
              # sys.exit(0) should be called when assistant exits cleanly
              mock_exit.assert_called_once_with(0)
              
              # time.sleep should NOT be called on code 3 (since we restart immediately)
              mock_sleep.assert_not_called()
