import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Keywords to pre-filter normal chat messages to optimize latency
ALARM_KEYWORDS = [
    "\u9b27\u9418", "\u63d0\u9192", "\u9b27\u9230", "\u5b9a\u6642", 
    "\u522a\u9664", "\u53d6\u6d88", "\u5217\u8868", "\u6e05\u55ae", "\u67e5\u770b", 
    "\u6539", "\u4fee\u6539", "\u66f4\u6539", "\u91cd\u8a2d",
    "\u660e\u5929", "\u65e9\u4e0a", "\u4e0b\u5348", "\u665a\u4e0a", "\u4eca\u665a", "\u660e\u65e9",
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
        if re.search('(?:[0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u534a]+)\\s*(?:\u9ede|\u5206|\u79d2|\u5c0f\u6642|\u5206\u9418|hour|min|sec|hr|m|s|:|\uff1a)', text_lower):
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
                "target_alarm": None,
                "repeat": None
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
            '  "target_alarm": "string or null (old label, old time, description, or ID to match which alarm to update or delete)",\n'
            '  "repeat": "daily | weekly:[days] | interval:[minutes] | null (recurrence rule: daily, weekly with days like 1,2,3 for Mon-Wed, or interval in minutes)"\n'
            "}\n\n"
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
                
            def clean_val(v):
                if isinstance(v, str):
                    v_clean = v.strip().lower()
                    if v_clean in ("null", "none", "無", "nil", ""):
                        return None
                return v

            return {
                "intent": result.get("intent", "none"),
                "time": clean_val(result.get("time")),
                "label": clean_val(result.get("label")),
                "alarm_id": clean_val(result.get("alarm_id")),
                "target_alarm": clean_val(result.get("target_alarm")),
                "repeat": clean_val(result.get("repeat"))
            }
        except Exception as e:
            logger.warning("Could not parse JSON from Ollama reply %r: %s", reply, e)
            return {
                "intent": "none",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": None,
                "repeat": None
            }

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()
        
        # Check list intent
        if any(w in text_lower for w in ["\u6709\u54ea\u4e9b\u9b27\u9418", "\u9b27\u9418\u6e05\u55ae", "\u9b27\u9418\u5217\u8868", "\u67e5\u770b\u9b27\u9418", "list alarm", "show alarm"]):
            return {
                "intent": "list_alarms",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": None,
                "repeat": None
            }
            
        # Check delete intent
        delete_match = re.search("(?:\u522a\u9664|\u53d6\u6d88|delete|cancel)(?:\\s*\u9b27\u9418)?\\s*(\\S+)", text_lower)
        if delete_match:
            val = delete_match.group(1).strip()
            # If val looks like a short hex ID (8 chars of hex or <= 8 ASCII alphanumeric)
            if re.match(r"^[a-f0-9]{8}$", val) or (len(val) <= 8 and re.match(r"^[a-zA-Z0-9]+$", val)):
                return {
                    "intent": "delete_alarm",
                    "time": None,
                    "label": None,
                    "alarm_id": val,
                    "target_alarm": None,
                    "repeat": None
                }
            else:
                return {
                    "intent": "delete_alarm",
                    "time": None,
                    "label": None,
                    "alarm_id": None,
                    "target_alarm": val,
                    "repeat": None
                }
            
        # Check update intent
        update_match = re.search("(?:\u6539|\u4fee\u6539|\u66f4\u6539|\u91cd\u8a2d|change|update|edit)(?:\\s*\u9b27\u9418)?\\s*(.+?)\\s*(?:\u70ba|\u5230|\u6539\u6210|to)\\s*(.+)", text_lower)
        if update_match:
            target = update_match.group(1).strip()
            return {
                "intent": "update_alarm",
                "time": None,
                "label": None,
                "alarm_id": None,
                "target_alarm": target,
                "repeat": None
            }

        # Check set repeating alarm fallback
        interval_match = re.search("\u6bcf(?:\\u9694)?\\s*([0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]*)\\s*\u5206\u9418", text_lower)
        if interval_match:
            num_str = interval_match.group(1)
            if not num_str:
                minutes = 1
            else:
                chinese_digits = {"\u4e00": 1, "\u4e8c": 2, "\u4e09": 3, "\u56db": 4, "\u4e94": 5, "\u516d": 6, "\u4e03": 7, "\u516b": 8, "\u4e5d": 9, "\u5341": 10}
                if num_str in chinese_digits:
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
                "repeat": f"interval:{minutes}"
            }

        return {
            "intent": "none",
            "time": None,
            "label": None,
            "alarm_id": None,
            "target_alarm": None,
            "repeat": None
        }
