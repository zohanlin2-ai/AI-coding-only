"""
Unit tests for file generation (saving code blocks) and DND format extensions in Ann's PyQt6 GUI.
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
    from PyQt6.QtWidgets import QApplication, QFileDialog
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog
        HAS_QT = True
    except ImportError:
        HAS_QT = False

# Skip all tests in this file if Qt is not available
pytestmark = pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 is required for GUI tests")

if HAS_QT:
    # Ensure QApplication is initialized (needed for widget creation)
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Add parent path to import assistant_gui
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from assistant_gui import parse_markdown_blocks, CodeBlockWidget, ChatWindow, FloatingBubble


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


def test_parse_markdown_blocks_plain_text():
    text = "Hello world! This is just text."
    blocks = parse_markdown_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text"
    assert blocks[0]["content"] == text


def test_parse_markdown_blocks_single_code():
    text = "Here is a code block:\n```python\nprint('hello')\n```\nHope it helps!"
    blocks = parse_markdown_blocks(text)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "text"
    assert blocks[0]["content"] == "Here is a code block:\n"
    
    assert blocks[1]["type"] == "code"
    assert blocks[1]["language"] == "python"
    assert blocks[1]["content"] == "print('hello')"
    
    assert blocks[2]["type"] == "text"
    assert blocks[2]["content"] == "\nHope it helps!"


def test_parse_markdown_blocks_multiple_code():
    text = "```html\n<h1>Title</h1>\n```\nAnd CSS:\n```css\nh1 { color: red; }\n```"
    blocks = parse_markdown_blocks(text)
    assert len(blocks) == 3
    
    assert blocks[0]["type"] == "code"
    assert blocks[0]["language"] == "html"
    assert blocks[0]["content"] == "<h1>Title</h1>"
    
    assert blocks[1]["type"] == "text"
    assert blocks[1]["content"] == "\nAnd CSS:\n"
    
    assert blocks[2]["type"] == "code"
    assert blocks[2]["language"] == "css"
    assert blocks[2]["content"] == "h1 { color: red; }"


def test_parse_markdown_blocks_no_lang():
    text = "```\nSome plain preformatted text\n```"
    blocks = parse_markdown_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["language"] == ""
    assert blocks[0]["content"] == "Some plain preformatted text"


def test_code_block_widget_init():
    widget = CodeBlockWidget("python", "print('test')")
    assert widget.language == "python"
    assert widget.code_content == "print('test')"
    assert widget.code_edit.toPlainText() == "print('test')"


def test_code_block_widget_save_to_file(tmp_path):
    code_content = "print('hello from saved block')"
    widget = CodeBlockWidget("python", code_content)
    
    save_path = tmp_path / "test_saved_code.py"
    
    # Mock QFileDialog.getSaveFileName to simulate user selecting a path
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(save_path), "Python Files (*.py)")) as mock_save:
        widget.save_to_file()
        
        # Verify getSaveFileName was called with correct filter mapping
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert "Python Files (*.py)" in args[3]  # The filters string parameter
        assert "code.py" in args[2]             # The default filename parameter
        
        # Verify file was written
        assert save_path.exists()
        assert save_path.read_text(encoding="utf-8") == code_content


def test_code_block_widget_save_to_file_unknown_lang(tmp_path):
    code_content = "unknown language content"
    widget = CodeBlockWidget("randomlang", code_content)
    
    save_path = tmp_path / "test_saved.txt"
    
    # Mock QFileDialog.getSaveFileName to simulate user selecting a path
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(save_path), "Text Files (*.txt)")) as mock_save:
        widget.save_to_file()
        
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert "Text Files (*.txt)" in args[3]  # Default fallback filter
        assert "code.txt" in args[2]            # Default fallback extension
        
        assert save_path.exists()
        assert save_path.read_text(encoding="utf-8") == code_content


def test_chat_window_dnd_new_extensions(mock_gui_components, tmp_path):
    c = mock_gui_components
    bubble = MagicMock()
    
    chat_win = ChatWindow(c["config"], c["controller"], bubble)
    
    new_extensions = ['.c', '.cpp', '.java', '.sh', '.ts', '.sql', '.toml', '.env', '.xml']
    
    for idx, ext in enumerate(new_extensions):
        test_file = tmp_path / f"test_{idx}{ext}"
        test_file.write_text("dummy content", encoding="utf-8")
        
        url = MagicMock()
        url.toLocalFile.return_value = str(test_file)
        
        mime_data = MagicMock()
        mime_data.hasUrls.return_value = True
        mime_data.urls.return_value = [url]
        
        drop_event = MagicMock()
        drop_event.mimeData.return_value = mime_data
        
        # Trigger dropEvent
        ChatWindow.dropEvent(chat_win, drop_event)
        
        # Verify it was added to attachments
        assert test_file in chat_win.attachments
        
    chat_win.clear_attachments()
