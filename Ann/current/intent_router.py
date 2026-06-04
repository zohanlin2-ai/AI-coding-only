"""
intent_router.py — Async-capable intent router and module registry.

IntentRouter maintains an ordered list of registered BaseIntentParser modules.
When route() is called, it iterates through modules in registration order:
  1. should_parse()  — fast keyword pre-filter (runs synchronously)
  2. parse_intent()  — Ollama-backed parsing (blocking, run from a worker thread)
  3. execute()       — module business logic (blocking, run from a worker thread)

Because every call to route() may block on Ollama, callers should always
invoke route() from a background thread (e.g. QThread / ThreadPoolExecutor),
never from the GUI main thread.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from base_intent_parser import BaseIntentParser, ModuleResult

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Registry and dispatcher for feature-module plugins.

    Usage:
        router = IntentRouter()
        router.register(alarm_parser)
        router.register(file_parser)
        router.register(news_parser)

        result = router.route(user_text, context)  # returns ModuleResult or None
    """

    def __init__(self) -> None:
        self._modules: list[BaseIntentParser] = []

    def register(self, module: BaseIntentParser) -> None:
        """Register a module plugin.  Modules are tried in registration order."""
        self._modules.append(module)
        logger.debug("IntentRouter: registered module %s", type(module).__name__)

    def route(self, text: str, context: dict) -> ModuleResult | None:
        """
        Try each registered module in order.  Return the first ModuleResult
        produced by a module whose intent matches, or None if no module matches.

        Args:
            text:    The raw user input string.
            context: Shared runtime context dict from CoreController.

        Returns:
            A ModuleResult on match, or None if no module claimed the intent.
        """
        for module in self._modules:
            # Fast pre-filter — skip Ollama call if keywords don't match
            if not module.should_parse(text):
                continue

            parsed = module.parse_intent(text)
            if parsed.get("intent", "none") == "none":
                continue

            logger.info(
                "IntentRouter: module %s claimed intent '%s' for text %r",
                type(module).__name__,
                parsed["intent"],
                text[:60],
            )
            return module.execute(parsed, context)

        return None
