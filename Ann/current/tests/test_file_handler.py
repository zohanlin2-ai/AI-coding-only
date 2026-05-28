"""
Unit tests for conversational file generation intent parsing and execution.
"""
import sys
from pathlib import Path
import pytest

# Add parent path to imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from file_handler import FileIntentParser, handle_file_intent, parse_markdown_blocks


def test_parse_markdown_blocks_basic():
    # Helper parser utility test
    text = "Plain text\n```python\nprint('hello')\n```\nMore text"
    blocks = parse_markdown_blocks(text)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "text"
    assert blocks[1]["type"] == "code"
    assert blocks[1]["language"] == "python"
    assert blocks[1]["content"] == "print('hello')"


def test_file_intent_parser_should_parse():
    parser = FileIntentParser("http://localhost:11434", "test-model")
    assert parser.should_parse("幫我儲存程式碼") is True
    assert parser.should_parse("匯出對話紀錄到 history.md") is True
    assert parser.should_parse("哈囉你好") is False


def test_file_intent_parser_regex_fallback():
    parser = FileIntentParser("http://localhost:11434", "test-model")
    
    # Export history tests
    parsed1 = parser._regex_fallback("匯出對話紀錄")
    assert parsed1["intent"] == "export_history"
    assert parsed1["filename"] == "conversation.md"
    
    parsed2 = parser._regex_fallback("把聊天紀錄存到 my_log.txt")
    assert parsed2["intent"] == "export_history"
    assert parsed2["filename"] == "my_log.txt"
    
    # Save code tests
    parsed3 = parser._regex_fallback("把剛才的程式碼存成 app.py")
    assert parsed3["intent"] == "save_code"
    assert parsed3["filename"] == "app.py"
    assert parsed3["target"] == "py"
    
    parsed4 = parser._regex_fallback("儲存為 index.html")
    assert parsed4["intent"] == "save_code"
    assert parsed4["filename"] == "index.html"
    assert parsed4["target"] == "html"
    
    # Non-file tests
    parsed5 = parser._regex_fallback("這是一個設定鬧鐘的提醒")
    assert parsed5["intent"] == "none"


def test_handle_file_intent_export_history(tmp_path):
    conversation = [
        {"role": "user", "content": "Hello Ann"},
        {"role": "assistant", "content": "Hello! How can I help you?"},
        {"role": "user", "content": "[Important: safety warning]\n\nUser: Please export history"},
    ]
    
    parsed = {
        "intent": "export_history",
        "filename": "chat_history.md",
        "target": None
    }
    
    reply = handle_file_intent(parsed, conversation, tmp_path)
    
    # Check that file was created
    expected_file = tmp_path / "chat_history.md"
    assert expected_file.exists()
    
    content = expected_file.read_text(encoding="utf-8")
    assert "### User\nHello Ann" in content
    assert "### Ann\nHello! How can I help you?" in content
    # Check that system wrapper is stripped
    assert "### User\nPlease export history" in content
    
    # Check return message formats clickable file path
    assert "chat_history.md" in reply
    assert "file:///" in reply


def test_handle_file_intent_save_code_basic(tmp_path):
    conversation = [
        {"role": "user", "content": "Write a python script"},
        {"role": "assistant", "content": "Sure! Here is a python script:\n```python\nprint('hello')\n```\nHope it works!"},
    ]
    
    parsed = {
        "intent": "save_code",
        "filename": "app.py",
        "target": "py"
    }
    
    reply = handle_file_intent(parsed, conversation, tmp_path)
    
    expected_file = tmp_path / "app.py"
    assert expected_file.exists()
    
    content = expected_file.read_text(encoding="utf-8")
    assert content == "print('hello')"
    assert "app.py" in reply
    assert "file:///" in reply


def test_handle_file_intent_save_code_multiple_languages(tmp_path):
    conversation = [
        {"role": "user", "content": "Write HTML and CSS"},
        {
            "role": "assistant", 
            "content": "Sure!\n```html\n<h1>Hello</h1>\n```\nAnd CSS:\n```css\nh1 { color: red; }\n```"
        },
    ]
    
    # Request to save CSS
    parsed = {
        "intent": "save_code",
        "filename": "style.css",
        "target": "css"
    }
    
    reply = handle_file_intent(parsed, conversation, tmp_path)
    
    expected_file = tmp_path / "style.css"
    assert expected_file.exists()
    assert expected_file.read_text(encoding="utf-8") == "h1 { color: red; }"
    
    # Request to save HTML specifically
    parsed_html = {
        "intent": "save_code",
        "filename": "index.html",
        "target": "html"
    }
    reply_html = handle_file_intent(parsed_html, conversation, tmp_path)
    expected_html = tmp_path / "index.html"
    assert expected_html.exists()
    assert expected_html.read_text(encoding="utf-8") == "<h1>Hello</h1>"


def test_handle_file_intent_errors(tmp_path):
    # No conversation history
    parsed = {
        "intent": "export_history",
        "filename": "test.md",
        "target": None
    }
    reply = handle_file_intent(parsed, [], tmp_path)
    assert "目前沒有對話紀錄可以匯出。" in reply
    
    # No code block present in history
    conversation = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    parsed_code = {
        "intent": "save_code",
        "filename": "app.py",
        "target": "py"
    }
    reply_code = handle_file_intent(parsed_code, conversation, tmp_path)
    assert "找不到可以儲存的程式碼區塊。" in reply_code
