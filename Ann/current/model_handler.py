"""
model_handler.py - LLM-backed intent parser for model query and switching.

Flow:
  1. should_parse()  - broad keyword pre-filter (fast, no LLM)
  2. parse_intent()  - LLM classifies intent as JSON
  3. execute()       - perform the action and return a reply

Supported intents:
  query_current   - user wants to know which model is currently in use
  query_available - user wants to list all installed/available models
  switch_model    - user wants to switch to a specific model
  none            - not a model management request
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from base_intent_parser import BaseIntentParser, ModuleResult

if TYPE_CHECKING:
    from core_controller import CoreController

logger = logging.getLogger(__name__)


class ModelIntentParser(BaseIntentParser):
    """
    LLM-backed intent parser for model management requests.
    Registered as a module in IntentRouter; receives the shared context dict
    from CoreController, which must include a 'controller' key.
    """

    KEYWORDS = [
        "model", "llm",
        "模型",   # 模型
        "切換",   # 切換
        "switch",
        "用哪個",  # 用哪個
        "有哪些",  # 有哪些
        "換成",   # 換成
        "改用",   # 改用
        "改換",   # 改換
        "available",
        "change to",
        "什麼 ai",  # 什麼ai
        "哪個 ai",  # 哪個ai
        "換個 ai",  # 換個ai
        "換 ai",        # 換ai
    ]

    def _build_system_prompt(self) -> str:
        return (
            "You are an intent classifier for LLM model management commands.\n"
            "Classify the user message and respond with JSON only - no explanation, "
            "no markdown fences.\n\n"
            "Possible intents:\n"
            "  \"query_current\"   - user wants to know which model is currently in use\n"
            "  \"query_available\" - user wants to list all installed/available models\n"
            "  \"switch_model\"    - user wants to switch to a specific model\n"
            "  \"none\"            - message is NOT about model management\n\n"
            "Response format (strict JSON, one line):\n"
            "{\"intent\": \"query_current\", \"model\": null}\n"
            "{\"intent\": \"query_available\", \"model\": null}\n"
            "{\"intent\": \"switch_model\", \"model\": \"<model name>\"}\n"
            "{\"intent\": \"none\", \"model\": null}"
        )

    def _validate_and_normalize(self, result: dict) -> dict:
        valid = {"query_current", "query_available", "switch_model", "none"}
        if result.get("intent") not in valid:
            result["intent"] = "none"
        if "model" not in result:
            result["model"] = None
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none", "model": None}

    def _regex_fallback(self, text: str) -> dict:
        switch_kws = [
            "切換到",  # 切換到
            "切換至",  # 切換至
            "換成",        # 換成
            "改用",        # 改用
            "switch to",
            "change to",
        ]
        text_lower = text.lower()
        for kw in switch_kws:
            if kw in text_lower:
                after = text[text_lower.find(kw) + len(kw):].strip()
                model = re.split(r"\s+", after)[0].strip("'\"") if after else ""
                return {"intent": "switch_model", "model": model or None}
        return {"intent": "none", "model": None}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        intent = parsed.get("intent", "none")
        model_name = parsed.get("model") or ""

        controller = context["controller"]
        config_path: Path = context["base_dir"] / "config.yml"

        if intent == "query_current":
            return ModuleResult(
                reply="目前使用的 LLM 模型是：" + controller.llm_model
            )

        if intent == "query_available":
            return ModuleResult(reply=_list_models(controller))

        if intent == "switch_model":
            return ModuleResult(reply=_switch_model(controller, config_path, model_name))

        return ModuleResult(reply="")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _list_models(controller) -> str:
    models = controller.ollama_client.get_installed_models()
    if not models:
        return (
            "目前 Ollama 中沒有已安裝的模型"
            "，或無法連線到 Ollama 服務。\n"
            "請確認 Ollama 正在執行：`ollama serve`"
        )
    current = controller.llm_model
    lines = ["目前 Ollama 中已安裝的模型："]
    for m in models:
        tag = "  ← 目前使用" if m == current else ""
        lines.append("• " + m + tag)
    lines.append(
        "\n如需切換，請說「切換到"
        " <模型名稱>」。"
    )
    return "\n".join(lines)


def _switch_model(controller, config_path: Path, model_name: str) -> str:
    if not model_name:
        return (
            "請告訴我要切換到哪個模型"
            "，例如「切換到 llama3」。\n"
            + _list_models(controller)
        )

    models = controller.ollama_client.get_installed_models()

    if model_name not in models:
        matches = [m for m in models if model_name.lower() in m.lower()]
        if len(matches) == 1:
            model_name = matches[0]
        elif len(matches) > 1:
            names = "、".join(matches)
            return (
                "找到多個符合的模型：" + names
                + "\n請指定完整名稱後再切換。"
            )
        else:
            return (
                "找不到模型「" + model_name + "」。\n"
                "請先執行 `ollama pull " + model_name
                + "` 安裝，或輸入「有哪些模型"
                "」查看已安裝清單。"
            )

    old_model = controller.llm_model
    if old_model == model_name:
        return (
            "目前已在使用 " + model_name
            + "，無需切換。"
        )

    controller.llm_model = model_name
    for module in controller.router._modules:
        if hasattr(module, "model"):
            module.model = model_name
    if hasattr(controller, "memory_manager") and hasattr(controller.memory_manager, "model"):
        controller.memory_manager.model = model_name

    try:
        content = config_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r"(  model:\s*)\S+",
            lambda m: m.group(1) + model_name,
            content,
        )
        config_path.write_text(new_content, encoding="utf-8")
        logger.info("Model switched: %s -> %s (saved to config.yml)", old_model, model_name)
    except Exception as e:
        logger.error("Failed to persist model switch to config.yml: %s", e)
        return (
            "已切換至模型 " + model_name
            + "（本次對話有效），"
            "但儲存設定檔時失敗：" + str(e)
        )

    return (
        "已成功從 " + old_model
        + " 切換至 " + model_name + "。"
    )
