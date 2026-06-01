"""
alarm_handler.py — shared alarm intent handling for CLI and GUI.

Both assistant.py (CLI) and assistant_gui.py (GUI) use this module
to avoid duplicating the same alarm intent dispatch logic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

# ---------------------------------------------------------------------------
# Update confirmation keyword lists (single source of truth)
# ---------------------------------------------------------------------------

UPDATE_YES_WORDS = [
    "好", "要", "更新", "ok", "yes", "y", "update", "sure",
    "確定", "可以", "對", "行", "同意", "升級", "安裝", "upgrade",
    "confirm", "現在", "即刻", "yer", "yeah", "yep", "yea",
]

UPDATE_NO_WORDS = [
    "不要", "不", "否", "later", "no", "n", "暫時", "取消",
    "晚點", "拒絕", "skip", "先不要", "等一下", "等會", "待會",
    "下次", "沒空", "忙", "暫不", "以後", "不升", "沒興趣",
    "沒時間", "改天", "忽略",
]

# Keywords that trigger an on-demand update check (single source of truth for CLI + GUI).
UPDATE_CHECK_WORDS = ["update", "更新", "檢查更新", "升級", "check update"]


def detect_update_intent(user_input_lower: str) -> str:
    """
    Returns 'yes', 'no', or 'unknown' based on update confirmation keywords.
    Negative words are checked first to avoid substring collisions (e.g. '不要' vs '要').
    """
    if "沒問題" in user_input_lower or "沒有問題" in user_input_lower:
        return "yes"
    if any(w in user_input_lower for w in UPDATE_NO_WORDS):
        return "no"
    if any(w in user_input_lower for w in UPDATE_YES_WORDS):
        return "yes"
    return "unknown"


# ---------------------------------------------------------------------------
# Alarm intent dispatcher
# ---------------------------------------------------------------------------

def handle_alarm_intent(
    parsed: dict,
    alarm_manager,
    call_llm: Callable[[str], str],
) -> str | None:
    """
    Dispatches a parsed alarm intent and returns the reply string,
    or None if the intent is 'none' (i.e. not an alarm request).

    Args:
        parsed:       Output of IntentParser.parse_intent().
        alarm_manager: AlarmManager instance.
        call_llm:     Callable that accepts a prompt string and returns
                      the LLM's reply string.  Callers inject this so
                      CLI and GUI can supply their own implementations.
    """
    intent = parsed.get("intent", "none")
    if intent == "none":
        return None

    if intent == "set_alarm":
        return _handle_set_alarm(parsed, alarm_manager, call_llm)
    if intent == "list_alarms":
        return _handle_list_alarms(alarm_manager, call_llm)
    if intent == "delete_alarm":
        return _handle_delete_alarm(parsed, alarm_manager, call_llm)
    if intent == "update_alarm":
        return _handle_update_alarm(parsed, alarm_manager, call_llm)

    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _handle_set_alarm(parsed: dict, alarm_manager, call_llm: Callable) -> str:
    time_str = parsed.get("time")
    label = parsed.get("label")
    repeat_pattern = parsed.get("repeat")

    if not time_str:
        return "請告訴我您想設定鬧鐘的具體時間。"

    try:
        dt = datetime.fromisoformat(time_str)
        success, msg_or_list, _ = alarm_manager.add_alarm(dt, label, repeat_pattern)
        if success:
            repeat_msg = f" repeating '{repeat_pattern}'" if repeat_pattern else ""
            prompt = (
                f"System instruction: The alarm was successfully set for "
                f"{dt.strftime('%Y-%m-%d %H:%M')}{repeat_msg} with label "
                f"'{label or '無'}'. Confirm this to the user in a friendly way."
            )
        else:
            prompt = (
                f"System instruction: The user wants to set an alarm but the "
                f"limit of 10 active alarms has been reached.\n"
                f"Here is the list of active alarms:\n{msg_or_list}\n"
                f"Please inform the user about the limit and present this list "
                f"of current alarms with their IDs, asking which one they would "
                f"like to delete to make room."
            )
        return call_llm(prompt)
    except Exception as ex:
        return f"設定鬧鐘時發生錯誤：{ex}"


def _handle_list_alarms(alarm_manager, call_llm: Callable) -> str:
    alarms = alarm_manager.get_alarms()
    if not alarms:
        return "您目前沒有設定任何鬧鐘。"
    alarms_list = "\n".join(
        f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M:%S')} — {a.label or '無備註'}"
        + (f" (重複: {a.repeat_pattern})" if a.repeat_pattern else "")
        for a in alarms
    )
    prompt = (
        f"System instruction: Present the following active alarms list to the "
        f"user in a friendly way:\n{alarms_list}"
    )
    return call_llm(prompt)


def _handle_delete_alarm(parsed: dict, alarm_manager, call_llm: Callable) -> str:
    alarm_id = parsed.get("alarm_id")
    label = parsed.get("label")
    target_alarm = parsed.get("target_alarm")

    try:
        success, msg, matches = alarm_manager.delete_alarm_flow(
            alarm_id=alarm_id,
            target_alarm=target_alarm,
            label=label,
        )
        if not success and len(matches) > 1:
            alarms_list = "\n".join(
                f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M')} — {a.label or '無備註'}"
                for a in matches
            )
            prompt = (
                f"System instruction: Multiple alarms matched the deletion query. "
                f"Present the list of matching alarms below and ask the user to "
                f"clarify which one they wish to delete by typing its ID (e.g. 'a1'):\n"
                f"{alarms_list}"
            )
            return call_llm(prompt)
        if success:
            return call_llm(
                f"System instruction: {msg} Confirm this successful deletion to the user in a friendly way."
            )
        return msg
    except Exception as ex:
        return f"刪除鬧鐘時發生錯誤：{ex}"


def _handle_update_alarm(parsed: dict, alarm_manager, call_llm: Callable) -> str:
    alarm_id = parsed.get("alarm_id")
    target_alarm = parsed.get("target_alarm")
    time_str = parsed.get("time")
    new_label = parsed.get("label")

    dt = None
    if time_str:
        try:
            dt = datetime.fromisoformat(time_str)
        except Exception:
            pass

    if not time_str and not new_label:
        return "請告訴我您想將鬧鐘修改成什麼時間或什麼備註名稱。"

    try:
        success, msg, matches = alarm_manager.update_alarm_flow(
            alarm_id=alarm_id,
            target_alarm=target_alarm,
            new_datetime=dt,
            new_label=new_label,
        )
        if not success and len(matches) > 1:
            alarms_list = "\n".join(
                f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M')} — {a.label or '無備註'}"
                for a in matches
            )
            prompt = (
                f"System instruction: Multiple alarms matched the update query. "
                f"Present the list of matching alarms below and ask the user to "
                f"clarify which one they wish to update by typing its ID (e.g. 'a1'):\n"
                f"{alarms_list}"
            )
            return call_llm(prompt)
        if success:
            return call_llm(
                f"System instruction: {msg} Confirm this successful update to the user in a friendly way."
            )
        return msg
    except Exception as ex:
        return f"修改鬧鐘時發生錯誤：{ex}"
