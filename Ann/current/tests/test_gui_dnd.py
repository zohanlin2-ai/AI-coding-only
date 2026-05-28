"""
Unit tests for the Drag & Drop (DND) functionality in Ann's PyQt6 GUI.
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
    from PyQt6.QtCore import Qt, QUrl, QPoint
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QUrl, QPoint
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
    from assistant_gui import FloatingBubble, ChatWindow, AttachmentItem, AttachmentViewerDialog, DragDropOverlay


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


def test_attachment_item_creation(tmp_path):
    # Create dummy attachment file
    file_path = tmp_path / "hello.txt"
    file_path.write_text("Hello World", encoding="utf-8")
    
    item = AttachmentItem(file_path)
    assert item.file_path == file_path
    
    # Test text files render with 📄 icon
    # icon_label is the first QLabel in the layout
    labels = item.findChildren(type(item.layout().itemAt(0).widget()))
    assert any(lbl.text() == "📄" for lbl in labels if hasattr(lbl, "text"))


def test_attachment_item_image_creation(tmp_path):
    # Create dummy image file name (not actual image bytes, but suffix checks)
    file_path = tmp_path / "test.png"
    
    item = AttachmentItem(file_path)
    assert item.file_path == file_path


def test_chat_window_dnd_handlers(mock_gui_components, tmp_path):
    c = mock_gui_components
    bubble = MagicMock()
    
    chat_win = ChatWindow(
        c["config"], c["evaluator"], bubble, c["alarm_manager"],
        c["alarm_trigger"], c["alarm_scheduler"], c["intent_parser"]
    )
    
    # Mock a drag enter event
    drag_event = MagicMock()
    mime_data = MagicMock()
    mime_data.hasUrls.return_value = True
    drag_event.mimeData.return_value = mime_data
    
    # Call drag enter
    chat_win.dragEnterEvent(drag_event)
    assert drag_event.acceptProposedAction.called
    assert not chat_win.drag_overlay.isHidden()
    
    # Call drag leave
    chat_win.dragLeaveEvent(drag_event)
    assert chat_win.drag_overlay.isHidden()
    
    # Mock drop event with text file URL
    txt_file = tmp_path / "code.py"
    txt_file.write_text("print('hello')", encoding="utf-8")
    
    url = MagicMock()
    url.toLocalFile.return_value = str(txt_file)
    mime_data.urls.return_value = [url]
    
    drop_event = MagicMock()
    drop_event.mimeData.return_value = mime_data
    
    chat_win.dropEvent(drop_event)
    assert drop_event.acceptProposedAction.called
    assert txt_file in chat_win.attachments
    assert not chat_win.attachment_tray.isHidden()
    
    # Clean up
    chat_win.clear_attachments()
    assert len(chat_win.attachments) == 0
    assert chat_win.attachment_tray.isHidden()


def test_floating_bubble_dnd_handlers(mock_gui_components, tmp_path):
    c = mock_gui_components
    
    bubble = FloatingBubble(
        c["config"], c["evaluator"], c["alarm_manager"],
        c["alarm_trigger"], c["alarm_scheduler"], c["intent_parser"]
    )
    
    # Initially drag is not active
    assert not bubble.drag_active
    
    # Mock drag enter
    drag_event = MagicMock()
    mime_data = MagicMock()
    mime_data.hasUrls.return_value = True
    drag_event.mimeData.return_value = mime_data
    
    bubble.dragEnterEvent(drag_event)
    assert drag_event.acceptProposedAction.called
    assert bubble.drag_active
    
    # Mock drop event
    txt_file = tmp_path / "notes.md"
    txt_file.write_text("# Notes", encoding="utf-8")
    
    url = MagicMock()
    url.toLocalFile.return_value = str(txt_file)
    mime_data.urls.return_value = [url]
    
    drop_event = MagicMock()
    drop_event.mimeData.return_value = mime_data
    
    # Mock expand_to_chat to prevent actual window visibility manipulation during test
    with patch.object(bubble, 'expand_to_chat') as mock_expand:
        bubble.dropEvent(drop_event)
        assert mock_expand.called
        assert drop_event.acceptProposedAction.called
        # Check that file was passed to chat window
        assert txt_file in bubble.chat_window.attachments
