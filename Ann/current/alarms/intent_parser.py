import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Keywords to pre-filter normal chat messages to optimize latency
ALARM_KEYWORDS = [
    "鬧鐘", "提醒", "鬧鈴", "定時", 
    "刪除", "取消", "列表", "清單", "查看", 
    "改", "修改", "更改", "重設",
    "明天", "早上", "下午", "晚上", "今晚", "明早",
    "alarm", "timer", "remind", "delete", "cancel", "list", "show", "clock",
    "change", "update", "edit"
]

class IntentParser:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def should_parse(self, text: str) -> bool:
        """Fast pre-filter to check if the query might be alarm-related."""
        text_lower = text.lower()
        # 1. Direct alarm keywords
        if any(keyword in text_lower for keyword in ALARM_KEYWORDS):
            return True
        # 2. Time-related digits/Chinese numbers patterns (e.g., 3點, 八點, 30分, 半小時)
        if re.search(r'(?:[0-9一二三四五六七八九十百半]+)\s*(?:點|分|秒|小時|分鐘|hour|min|sec|hr|m|s|:|：)', text_lower):
            return True
        return False

    def parse_intent(self, text: str) -> dict:
        """
        Sends the user text to Ollama for intent parsing and parameter extraction.
        Returns a dict conforming to the spec.
        """
        if not self.should_parse(text):
            return {
                "intent": "none",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": None
            }

        now_str = datetime.now().isoformat()
        
        system_prompt = (
            "You are an intent parser for an alarm assistant.\n"
            f"The current datetime is: {now_str}.\n\n"
            "Extract the user's alarm intent from the message below.\n"
            "Respond ONLY with a valid JSON object. No explanation, no markdown.\n\n"
            "JSON schema:\n"
            "{\n"
            '  "intent": "set_alarm | list_alarms | delete_alarm | update_alarm | none",\n'
            '  "time": "ISO-8601 datetime of the new time or null",\n'
            '  "label": "string or null (new label/remark if setting or updating)",\n'
            '  "alarm_id": "string or null (ID for delete or update)",\n'
            '  "target_alarm": "string or null (old label, old time, description, or ID to match which alarm to update or delete)"\n'
            "}\n\n"
            "Rules:\n"
            "- For relative times like '30 minutes later', calculate from current datetime.\n"
            "- For 'tonight at 11:50 PM', use today's date.\n"
            "- For 'tomorrow morning at 8', use tomorrow's date.\n"
            "- If the user says a time without a date and it has already passed today, assume today unless context implies otherwise.\n"
            "- label is optional free text the user wants attached to the alarm.\n"
            "- alarm_id is used only for delete_alarm or update_alarm intent if user specifies ID.\n"
            "- target_alarm is used for delete_alarm or update_alarm to identify which alarm (e.g. '下午3點', '開會').\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        try:
            from assistant import call_ollama
            reply = call_ollama(self.base_url, self.model, messages)
            parsed = self._clean_and_parse_json(reply)
            if parsed["intent"] == "none":
                # Fallback to regex check if Ollama returned non-JSON or could not parse
                fallback = self._regex_fallback(text)
                if fallback["intent"] != "none":
                    return fallback
            return parsed
        except Exception as e:
            logger.error("Failed to parse alarm intent using Ollama: %s", e)
            # Try a very basic regex fallback for list and delete to keep it working
            return self._regex_fallback(text)

    def _clean_and_parse_json(self, reply: str) -> dict:
        """Extracts JSON substring from the reply and parses it."""
        try:
            # Strip markdown formatting
            cleaned = reply.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()

            # Find matching curly braces if there's surrounding text
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)

            result = json.loads(cleaned)
            
            # Basic validation of schema fields
            if "intent" not in result:
                result["intent"] = "none"
            if result.get("intent") not in ["set_alarm", "list_alarms", "delete_alarm", "update_alarm", "none"]:
                result["intent"] = "none"
                
            return {
                "intent": result.get("intent", "none"),
                "time": result.get("time"),
                "label": result.get("label"),
                "alarm_id": result.get("alarm_id"),
                "target_alarm": result.get("target_alarm")
            }
        except Exception as e:
            logger.warning("Could not parse JSON from Ollama reply %r: %s", reply, e)
            return {
                "intent": "none",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": None
            }

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()
        
        # Check list intent
        if any(w in text_lower for w in ["有哪些鬧鐘", "鬧鐘清單", "鬧鐘列表", "查看鬧鐘", "list alarm", "show alarm"]):
            return {
                "intent": "list_alarms",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": None
            }
            
        # Check delete intent
        delete_match = re.search(r"(?:刪除|取消|delete|cancel)(?:\s*鬧鐘)?\s*([a-zA-Z0-9]+)", text_lower)
        if delete_match:
            alarm_id = delete_match.group(1)
            return {
                "intent": "delete_alarm",
                "time": None,
                "label": None,
                "alarm_id": alarm_id,
                "target_alarm": None
            }
            
        # Check update intent
        update_match = re.search(r"(?:改|修改|更改|重設|change|update|edit)(?:\s*鬧鐘)?\s*(.+?)\s*(?:為|到|改成|to)\s*(.+)", text_lower)
        if update_match:
            target = update_match.group(1)
            return {
                "intent": "update_alarm",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": target
            }

        return {
            "intent": "none",
            "time": None,
            "label": None,
            "alarm_id": None,
            "target_alarm": None
        }
