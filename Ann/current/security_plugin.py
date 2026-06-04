"""
security_plugin.py — Security mode intent parser plugin for Ann.

Handles requests to enter/exit security monitoring mode and simple
status queries. Integrates with the QStackedWidget-based Security
Dashboard in assistant_gui.py via [SECURITY_ON] / [SECURITY_OFF] markers.
"""
from __future__ import annotations

from base_intent_parser import BaseIntentParser, ModuleResult


class SecurityIntentParser(BaseIntentParser):
    """
    Plugin that detects security mode switch requests and basic status queries.

    On match, execute() returns a reply string that includes either
    [SECURITY_ON] or [SECURITY_OFF] so the GUI can switch its view.
    This follows the same marker pattern used by [EXIT] and [RESTART].
    """

    KEYWORDS = [
        # 中文
        "安全模式", "安全監控", "開啟監控", "關閉監控",
        "資安模式", "資安監控", "security mode",
        # 查詢類
        "有幾個告警", "有多少告警", "告警狀態", "daemon 狀態",
        "security alert", "安全告警",
    ]

    def _build_system_prompt(self) -> str:
        return (
            "You are an intent parser. Classify the user's message into one of these intents "
            "and respond ONLY with valid JSON.\n"
            "Intents:\n"
            '  "enable_security"  — user wants to enter/enable security monitoring mode\n'
            '  "disable_security" — user wants to exit/disable security monitoring mode\n'
            '  "query_status"     — user is asking about security alerts or daemon status\n'
            '  "none"             — not related to security mode\n\n'
            'Respond ONLY with: {"intent": "<one of the above>"}'
        )

    def _validate_and_normalize(self, result: dict) -> dict:
        allowed = {"enable_security", "disable_security", "query_status", "none"}
        if result.get("intent") not in allowed:
            result["intent"] = "none"
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none"}

    def _regex_fallback(self, text: str) -> dict:
        t = text.lower()
        disable_words = ["關閉", "退出", "離開", "exit", "disable", "off", "stop"]
        enable_words = ["開啟", "進入", "啟動", "enable", "on", "start", "切換"]
        query_words = ["幾個", "多少", "狀態", "status", "alert", "告警"]

        if "安全" in t or "security" in t or "監控" in t or "資安" in t:
            if any(w in t for w in disable_words):
                return {"intent": "disable_security"}
            if any(w in t for w in enable_words):
                return {"intent": "enable_security"}
            if any(w in t for w in query_words):
                return {"intent": "query_status"}
            return {"intent": "enable_security"}
        if any(w in t for w in ["告警", "alert"]):
            return {"intent": "query_status"}
        return {"intent": "none"}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        intent = parsed.get("intent", "none")

        if intent == "enable_security":
            return ModuleResult(
                reply="已切換至安全監控模式，正在監控系統活動。[SECURITY_ON]"
            )

        if intent == "disable_security":
            return ModuleResult(
                reply="已退出安全監控模式，恢復一般對話。[SECURITY_OFF]"
            )

        if intent == "query_status":
            # Return a simple mock status summary; Phase 2 will read real data.
            return ModuleResult(
                reply=(
                    "🛡️ 安全監控摘要（Mock）：\n"
                    "• Daemon 狀態：Running\n"
                    "• Queue 深度：12 / 10,000\n"
                    "• 最近 1 小時告警：4 筆（1 筆 Critical）\n"
                    "如需查看詳細告警，請說「開啟安全模式」切換至 Security Dashboard。"
                )
            )

        return ModuleResult(reply="")
