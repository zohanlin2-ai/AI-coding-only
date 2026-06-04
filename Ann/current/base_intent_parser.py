"""
base_intent_parser.py — shared skeleton for LLM-based intent parsers.

All intent parsers (alarm, file, news, and future ones) follow the same pattern:
  1. should_parse(text) — fast keyword pre-filter
  2. parse_intent(text) — call Ollama, clean JSON, fall back to regex
  3. _clean_and_parse_json(reply) — strip markdown, extract JSON, normalize keys

Subclasses must implement:
  - KEYWORDS: list[str]           — used by the default should_parse()
  - _build_system_prompt() -> str — returns the Ollama system prompt
  - _validate_and_normalize(result: dict) -> dict
                                  — validates intent field and normalizes fields
  - _empty_result() -> dict       — returned when should_parse() is False or on error
  - _regex_fallback(text: str) -> dict — domain-specific rule-based fallback
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModuleResult:
    """
    Standardized result returned by a module's execute() method.

    Attributes:
        reply:    The text response to display to the user.
        articles: Optional list of news article dicts (for news card rendering in GUI).
        marker:   Optional control marker such as '[EXIT]', '[RESTART]', '[UPDATE]'.
    """
    reply: str
    articles: list = field(default_factory=list)
    marker: str | None = None


class BaseIntentParser:
    """
    Template base class for keyword-pre-filtered, Ollama-backed intent parsers.
    """

    # Subclasses set this at class level.
    KEYWORDS: list[str] = []

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_parse(self, text: str) -> bool:
        """Fast pre-filter. Returns True if text might need intent parsing."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.KEYWORDS)

    def parse_intent(self, text: str) -> dict:
        """
        Full intent parsing pipeline:
          should_parse → Ollama → _clean_and_parse_json → _regex_fallback
        """
        if not self.should_parse(text):
            return self._empty_result()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": text},
        ]

        try:
            from ollama_client import OllamaClient
            client = OllamaClient(self.base_url)
            reply = client.chat(self.model, messages)
            parsed = self._clean_and_parse_json(reply)
            if parsed.get("intent") == "none":
                fallback = self._regex_fallback(text)
                if fallback.get("intent") != "none":
                    return fallback
            return parsed
        except Exception as e:
            logger.error("%s failed to parse intent via Ollama: %s", type(self).__name__, e)
            return self._regex_fallback(text)

    # ------------------------------------------------------------------
    # Shared implementation — shared by all subclasses
    # ------------------------------------------------------------------

    def _clean_and_parse_json(self, reply: str) -> dict:
        """
        Strips markdown fences, extracts the first {...} block, parses JSON,
        normalizes keys, then delegates field validation to _validate_and_normalize().
        """
        try:
            cleaned = reply.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()

            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)

            result = json.loads(cleaned)
            if isinstance(result, dict):
                result = {k.strip().strip('"').strip("'").strip(): v
                          for k, v in result.items()}

            return self._validate_and_normalize(result)
        except Exception as e:
            logger.warning("%s could not parse JSON from reply %r: %s",
                           type(self).__name__, reply, e)
            return self._empty_result()

    @staticmethod
    def _clean_val(v):
        """Converts null-like strings ('null', 'none', '無', '') to None."""
        if isinstance(v, str):
            if v.strip().lower() in ("null", "none", "無", "nil", ""):
                return None
        return v

    # ------------------------------------------------------------------
    # Abstract interface — subclasses must implement these
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:  # pragma: no cover
        raise NotImplementedError

    def _validate_and_normalize(self, result: dict) -> dict:  # pragma: no cover
        raise NotImplementedError

    def _empty_result(self) -> dict:  # pragma: no cover
        raise NotImplementedError

    def _regex_fallback(self, text: str) -> dict:  # pragma: no cover
        raise NotImplementedError

    def execute(self, parsed: dict, context: dict) -> ModuleResult:  # pragma: no cover
        """
        Execute the module's action given a successfully parsed intent dict and a
        shared context dict provided by CoreController.  Subclasses must override
        this method to implement their domain-specific business logic.

        Args:
            parsed:  Output of parse_intent() with intent != 'none'.
            context: Shared runtime context containing config, conversation,
                     base_dir, user_text, call_llm, alarm_manager, news_manager.

        Returns:
            A ModuleResult with at least a reply string.
        """
        raise NotImplementedError
