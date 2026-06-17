"""
Integration tests for the E1 moral escalation confirmation mechanism (spec §19).

Covers the [MORAL_CONFIRM] wiring across CoreController and the GUI:
  - an E1 escalation pauses with a [MORAL_CONFIRM] marker and stashes the request
  - resume_after_moral_confirm replays the request with the moral gate approved
  - cancel_moral_confirm discards the pending request
  - the GUI sets/clears awaiting_moral_confirm and routes yes/no correctly
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core_controller import CoreController, ControllerResult
from moral_evaluator import Decision, MoralResult, RiskLevel


# ---------------------------------------------------------------------------
# Controller-level wiring (no Qt required)
# ---------------------------------------------------------------------------

def _make_controller():
    """A CoreController with only the attributes post_message's E1 path touches."""
    c = CoreController.__new__(CoreController)
    c.soul_manager = MagicMock()
    c.llm_available = False
    c.moral_policy = None
    c.pending_moral_action = None
    c.base_dir = Path(".")
    c.evaluator = MagicMock()
    return c


def test_e1_escalation_returns_moral_confirm_marker(tmp_path):
    c = _make_controller()
    c.base_dir = tmp_path
    forced = MoralResult(
        RiskLevel.HIGH, Decision.ESCALATE_OR_PAUSE, "This needs your confirmation.",
        0.82, escalation_level="E1",
    )
    c.evaluator.evaluate.return_value = forced

    result = c.post_message("do the risky thing")

    assert result.marker == "[MORAL_CONFIRM]"
    assert result.escalation_level == "E1"
    assert c.pending_moral_action is not None
    assert c.pending_moral_action["moral_result"] is forced
    assert c.pending_moral_action["user_text"] == "do the risky thing"


def test_non_e1_escalation_does_not_pause(tmp_path):
    # E3/E4 are advisory refusals, not a yes/no pause.
    c = _make_controller()
    c.base_dir = tmp_path
    forced = MoralResult(
        RiskLevel.HIGH, Decision.ESCALATE_OR_PAUSE, "Consult a professional.",
        0.82, escalation_level="E4",
    )
    c.evaluator.evaluate.return_value = forced

    result = c.post_message("loan question")

    assert result.marker is None
    assert result.is_refusal is True
    assert c.pending_moral_action is None


def test_resume_replays_with_approved_moral():
    c = _make_controller()
    forced = MoralResult(RiskLevel.HIGH, Decision.ESCALATE_OR_PAUSE, "ok", 0.82,
                         escalation_level="E1")
    c.pending_moral_action = {
        "user_text": "risky thing",
        "attachment_text": "",
        "images": [],
        "moral_result": forced,
    }
    captured = {}

    def fake_post(user_text, attachment_text="", images=None, _approved_moral=None):
        captured["user_text"] = user_text
        captured["approved"] = _approved_moral
        return ControllerResult(reply="proceeded")

    c.post_message = fake_post
    result = c.resume_after_moral_confirm()

    assert result.reply == "proceeded"
    assert captured["user_text"] == "risky thing"
    assert captured["approved"] is forced
    assert c.pending_moral_action is None  # cleared after resume


def test_resume_without_pending_is_safe():
    c = _make_controller()
    c.pending_moral_action = None
    result = c.resume_after_moral_confirm()
    assert "no pending" in result.reply.lower()


def test_cancel_clears_pending():
    c = _make_controller()
    c.pending_moral_action = {"user_text": "x"}
    c.cancel_moral_confirm()
    assert c.pending_moral_action is None


# ---------------------------------------------------------------------------
# GUI-level wiring (requires Qt)
# ---------------------------------------------------------------------------

os.environ["QT_QPA_PLATFORM"] = "offscreen"

HAS_QT = False
try:
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        HAS_QT = True
    except ImportError:
        HAS_QT = False

if HAS_QT:
    _app = QApplication.instance() or QApplication(sys.argv)
    from assistant_gui import ChatWindow


@pytest.fixture
def chat_window():
    config = {
        "llm": {"model": "test-model", "base_url": "http://localhost:11434"},
        "alarm": {"sound_path": "test.wav", "volume": 0.5},
    }
    controller = MagicMock()
    controller.alarm_manager = MagicMock()
    controller.alarm_trigger = MagicMock()
    controller.alarm_scheduler = MagicMock()
    return ChatWindow(config, controller, MagicMock())


@pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 required")
def test_gui_moral_confirm_marker_sets_awaiting(chat_window):
    result = ControllerResult(
        reply="⚠️ This needs confirmation.\n\nDo you want to continue? (yes / no)",
        marker="[MORAL_CONFIRM]", escalation_level="E1",
    )
    chat_window.handle_controller_result(result)
    assert chat_window.awaiting_moral_confirm is True


@pytest.mark.skipif(not HAS_QT, reason="PyQt6 or PySide6 required")
def test_gui_moral_confirm_no_cancels(chat_window):
    chat_window.awaiting_moral_confirm = True
    chat_window.input_field.setText("no")
    chat_window.send_message()
    chat_window.controller.cancel_moral_confirm.assert_called_once()
    assert chat_window.awaiting_moral_confirm is False
