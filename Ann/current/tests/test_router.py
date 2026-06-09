"""
tests/test_router.py — Unit tests for IntentRouter and module plugin interface.

Tests run without a real Ollama instance by patching parse_intent and execute()
at the module level.
"""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from base_intent_parser import BaseIntentParser, ModuleResult
from intent_router import IntentRouter


# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------

class _StubParser(BaseIntentParser):
    """Minimal parser that always claims intent 'stub' when keyword present."""

    KEYWORDS = ["stub_keyword"]

    def _build_system_prompt(self) -> str:
        return "stub"

    def _validate_and_normalize(self, result: dict) -> dict:
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none"}

    def _regex_fallback(self, text: str) -> dict:
        return {"intent": "stub", "data": text}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        return ModuleResult(reply=f"stub handled: {parsed['data']}")


class _NoneParser(BaseIntentParser):
    """Parser that never matches."""

    KEYWORDS = ["never_keyword"]

    def _build_system_prompt(self) -> str:
        return "none"

    def _validate_and_normalize(self, result: dict) -> dict:
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none"}

    def _regex_fallback(self, text: str) -> dict:
        return {"intent": "none"}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        return ModuleResult(reply="should not be called")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModuleResult:
    def test_defaults(self):
        r = ModuleResult(reply="hello")
        assert r.reply == "hello"
        assert r.data == {}
        assert r.marker is None

    def test_custom_fields(self):
        r = ModuleResult(reply="ok", data={"articles": [{"title": "A"}]}, marker="[EXIT]")
        assert r.data["articles"] == [{"title": "A"}]
        assert r.marker == "[EXIT]"


class TestIntentRouter:
    def _make_stub_parser(self):
        """Return a _StubParser that bypasses Ollama by using regex_fallback directly."""
        p = _StubParser(base_url="http://localhost:11434", model="test")
        # Patch parse_intent to call _regex_fallback directly (no Ollama needed)
        p.parse_intent = lambda text: p._regex_fallback(text)
        return p

    def _make_none_parser(self):
        p = _NoneParser(base_url="http://localhost:11434", model="test")
        p.parse_intent = lambda text: p._regex_fallback(text)
        return p

    def test_register_and_route_match(self):
        router = IntentRouter()
        parser = self._make_stub_parser()
        router.register(parser)

        result = router.route("stub_keyword something", context={})
        assert result is not None
        assert "stub handled" in result.reply

    def test_route_no_match_returns_none(self):
        router = IntentRouter()
        parser = self._make_stub_parser()
        router.register(parser)

        # Message doesn't contain 'stub_keyword' → should_parse returns False
        result = router.route("completely unrelated message", context={})
        assert result is None

    def test_route_skips_none_intent(self):
        """should_parse passes but parse_intent returns none → skip to next module."""
        router = IntentRouter()
        none_parser = self._make_none_parser()
        stub_parser = self._make_stub_parser()

        # none_parser has keyword 'never_keyword' which won't match, but we'll
        # test with a parser whose should_parse passes but returns none intent.
        class _FalsePositiveParser(BaseIntentParser):
            KEYWORDS = ["stub_keyword"]  # same keyword → should_parse passes

            def _build_system_prompt(self):
                return ""

            def _validate_and_normalize(self, r):
                return r

            def _empty_result(self):
                return {"intent": "none"}

            def _regex_fallback(self, text):
                return {"intent": "none"}  # always returns none

            def execute(self, parsed, context):
                return ModuleResult(reply="should not reach here")

        false_parser = _FalsePositiveParser("http://localhost:11434", "test")
        false_parser.parse_intent = lambda text: false_parser._regex_fallback(text)

        router.register(false_parser)
        router.register(stub_parser)

        result = router.route("stub_keyword hello", context={})
        # false_parser's intent is 'none' → should fall through to stub_parser
        assert result is not None
        assert "stub handled" in result.reply

    def test_registration_order_matters(self):
        """First registered module that claims the intent wins."""
        router = IntentRouter()

        class _PriorityParser(BaseIntentParser):
            KEYWORDS = ["stub_keyword"]

            def _build_system_prompt(self):
                return ""

            def _validate_and_normalize(self, r):
                return r

            def _empty_result(self):
                return {"intent": "none"}

            def _regex_fallback(self, text):
                return {"intent": "priority", "data": text}

            def execute(self, parsed, context):
                return ModuleResult(reply="priority wins")

        priority = _PriorityParser("http://localhost:11434", "test")
        priority.parse_intent = lambda text: priority._regex_fallback(text)
        fallback = self._make_stub_parser()

        router.register(priority)
        router.register(fallback)

        result = router.route("stub_keyword test", context={})
        assert result.reply == "priority wins"

    def test_empty_router_returns_none(self):
        router = IntentRouter()
        assert router.route("any text", context={}) is None

    def test_multiple_modules_registered(self):
        router = IntentRouter()
        parser1 = self._make_stub_parser()
        parser2 = self._make_stub_parser()
        router.register(parser1)
        router.register(parser2)
        # Should still return a result from the first match
        result = router.route("stub_keyword", context={})
        assert result is not None
