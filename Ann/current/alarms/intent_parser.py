import logging
import re
from datetime import datetime, timedelta

from base_intent_parser import BaseIntentParser, ModuleResult

logger = logging.getLogger(__name__)

# Keywords to pre-filter normal chat messages to optimize latency
ALARM_KEYWORDS = [
    "鬧鐘", "提醒", "鬧到", "定時",
    "刪除", "取消", "列表", "清單", "查看",
    "改", "修改", "更改", "重設",
    "明天", "早上", "下午", "晚上", "今晚", "明早",
    "alarm", "timer", "remind", "delete", "cancel", "list", "show", "clock",
    "change", "update", "edit"
]

_ALARM_SYSTEM_PROMPT_TEMPLATE = (
    "You are an intent parser for an alarm assistant.\n"
    "The current datetime is: {now}.\n\n"
    "Extract the user's alarm intent from the message below.\n"
    "Respond ONLY with a valid JSON object. No explanation, no markdown.\n\n"
    "JSON schema:\n"
    "{{\n"
    '  "intent": "set_alarm | list_alarms | delete_alarm | update_alarm | none",\n'
    '  "time": "ISO-8601 datetime of the new time or null",\n'
    '  "label": "string or null (new label/remark if setting or updating)",\n'
    '  "alarm_id": "string or null (ID for delete or update)",\n'
    '  "target_alarm": "string or null (old label, old time, description, or ID to match which alarm to update or delete)",\n'
    '  "repeat": "daily | weekly:[days] | interval:[minutes] | null (recurrence rule: daily, weekly with days like 1,2,3 for Mon-Wed, or interval in minutes)"\n'
    "}}\n\n"
    "Rules:\n"
    "- For relative times like '30 minutes later', calculate from current datetime.\n"
    "- For 'tonight at 11:50 PM', use today's date.\n"
    "- For 'tomorrow morning at 8', use tomorrow's date.\n"
    "- If the user says a time without a date and it has already passed today, assume today unless context implies otherwise.\n"
    "- label is optional free text the user wants attached to the alarm.\n"
    "- alarm_id is used only for delete_alarm or update_alarm intent if user specifies ID.\n"
    "- target_alarm is used for delete_alarm or update_alarm to identify which alarm (e.g. '下午3點', '開會').\n"
    "- repeat specifies recurrence. 'every day at 8am' -> 'daily', 'every Monday and Wed' -> 'weekly:1,3', 'every minute' -> 'interval:1', 'every 10 minutes' -> 'interval:10', normal alarms -> null.\n"
)

_VALID_ALARM_INTENTS = {"set_alarm", "list_alarms", "delete_alarm", "update_alarm", "none"}


class IntentParser(BaseIntentParser):
    KEYWORDS = ALARM_KEYWORDS

    def should_parse(self, text: str) -> bool:
        """Alarm parser also triggers on time-related digit/Chinese patterns."""
        if super().should_parse(text):
            return True
        return bool(re.search(
            r'(?:[0-9一二三四五六七八九十百半]+)\s*(?:點|分|秒|小時|分鐘|hour|min|sec|hr|m|s|:|：)',
            text.lower()
        ))

    def _build_system_prompt(self) -> str:
        return _ALARM_SYSTEM_PROMPT_TEMPLATE.format(now=datetime.now().isoformat())

    def _validate_and_normalize(self, result: dict) -> dict:
        intent = result.get("intent", "none")
        if intent not in _VALID_ALARM_INTENTS:
            intent = "none"
        return {
            "intent": intent,
            "time": self._clean_val(result.get("time")),
            "label": self._clean_val(result.get("label")),
            "alarm_id": self._clean_val(result.get("alarm_id")),
            "target_alarm": self._clean_val(result.get("target_alarm")),
            "repeat": self._clean_val(result.get("repeat")),
        }

    def _empty_result(self) -> dict:
        return {
            "intent": "none",
            "time": None,
            "label": None,
            "alarm_id": None,
            "target_alarm": None,
            "repeat": None,
        }

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()

        # Check list intent
        if any(w in text_lower for w in ["有哪些鬧鐘", "鬧鐘清單", "鬧鐘列表", "查看鬧鐘", "list alarm", "show alarm"]):
            return {**self._empty_result(), "intent": "list_alarms"}

        # Check delete intent
        delete_match = re.search(r"(?:刪除|取消|delete|cancel)(?:\s*鬧鐘)?\s*(\S+)", text_lower)
        if delete_match:
            val = delete_match.group(1).strip()
            if re.match(r"^[a-f0-9]{8}$", val) or (len(val) <= 8 and re.match(r"^[a-zA-Z0-9]+$", val)):
                return {**self._empty_result(), "intent": "delete_alarm", "alarm_id": val}
            return {**self._empty_result(), "intent": "delete_alarm", "target_alarm": val}

        # Check update intent
        update_match = re.search(
            r"(?:改|修改|更改|重設|change|update|edit)(?:\s*鬧鐘)?\s*(.+?)\s*(?:為|到|改成|to)\s*(.+)",
            text_lower
        )
        if update_match:
            return {**self._empty_result(), "intent": "update_alarm",
                    "target_alarm": update_match.group(1).strip()}

        # Check set repeating alarm fallback
        interval_match = re.search(r"每(?:隔)?\s*([0-9一二三四五六七八九十]*)\s*分鐘", text_lower)
        if interval_match:
            num_str = interval_match.group(1)
            chinese_digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            if not num_str:
                minutes = 1
            elif num_str in chinese_digits:
                minutes = chinese_digits[num_str]
            else:
                try:
                    minutes = int(num_str)
                except ValueError:
                    minutes = 1
            trigger_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
            return {
                "intent": "set_alarm",
                "time": trigger_time,
                "label": "每分鐘鬧鐘" if minutes == 1 else f"每{minutes}分鐘鬧鐘",
                "alarm_id": None,
                "target_alarm": None,
                "repeat": f"interval:{minutes}",
            }

        return self._empty_result()

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        """Dispatch the parsed alarm intent and return the LLM reply as a ModuleResult."""
        from alarm_handler import handle_alarm_intent
        reply = handle_alarm_intent(
            parsed,
            context["alarm_manager"],
            context["call_llm"],
        )
        return ModuleResult(reply=reply or "")

