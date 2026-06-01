import re
import logging
from datetime import datetime

from base_intent_parser import BaseIntentParser

logger = logging.getLogger(__name__)

NEWS_KEYWORDS = [
    "新聞", "news", "摘要", "這篇", "reuters", "google news", "報導", "消息", "來源",
    "詳細說明", "詳細", "summarize", "summary", "article", "feed", "rss", "找新聞", "看新聞"
]

_NEWS_SYSTEM_PROMPT_TEMPLATE = (
    "You are an intent parser for a news assistant.\n"
    "The current datetime is: {now}.\n\n"
    "Extract the user's news query intent from the message below.\n"
    "Respond ONLY with a valid JSON object. No explanation, no markdown.\n\n"
    "JSON schema:\n"
    "{{\n"
    '  "intent": "query_news | summarize_article | filter_by_keyword | list_sources | none",\n'
    '  "keywords": ["string"] or [],\n'
    '  "category": "technology | finance | politics | sports | health | entertainment | general | null",\n'
    '  "source": "string or null",\n'
    '  "article_url": "string or null"\n'
    "}}\n\n"
    "Rules:\n"
    "- keywords: extract relevant search terms from the user message.\n"
    "- category: infer the most relevant category (technology, finance, politics, sports, health, entertainment, general), or null if unclear.\n"
    "- source: only populate if the user explicitly names a specific source (e.g. 'reuters', 'google news').\n"
    "- article_url: only populate for summarize_article intent. Extract any HTTP/HTTPS URL found in the message.\n"
)

_VALID_NEWS_INTENTS = {"query_news", "summarize_article", "filter_by_keyword", "list_sources", "none"}
_VALID_CATEGORIES = {"technology", "finance", "politics", "sports", "health", "entertainment", "general"}


class NewsIntentParser(BaseIntentParser):
    KEYWORDS = NEWS_KEYWORDS

    def should_parse(self, text: str) -> bool:
        """News parser also triggers on HTTP/HTTPS URLs."""
        if super().should_parse(text):
            return True
        return bool(re.search(r"https?://\S+", text))

    def _build_system_prompt(self) -> str:
        return _NEWS_SYSTEM_PROMPT_TEMPLATE.format(now=datetime.now().isoformat())

    def _validate_and_normalize(self, result: dict) -> dict:
        intent = result.get("intent", "none")
        if intent not in _VALID_NEWS_INTENTS:
            intent = "none"

        keywords = result.get("keywords")
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k) for k in keywords]

        category = self._clean_val(result.get("category"))
        if category not in _VALID_CATEGORIES:
            category = None

        source = self._clean_val(result.get("source"))

        article_url = result.get("article_url")
        if article_url:
            article_url = str(article_url).strip()
            if not (article_url.startswith("http://") or article_url.startswith("https://")):
                article_url = None

        return {
            "intent": intent,
            "keywords": keywords,
            "category": category,
            "source": source,
            "article_url": article_url,
        }

    def _empty_result(self) -> dict:
        return {
            "intent": "none",
            "keywords": [],
            "category": None,
            "source": None,
            "article_url": None,
        }

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()

        url_match = re.search(r"(https?://\S+)", text)
        url = url_match.group(1) if url_match else None

        if url and any(w in text_lower for w in ["摘要", "這篇", "說明", "summary", "summarize"]):
            return {**self._empty_result(), "intent": "summarize_article", "article_url": url}

        if any(w in text_lower for w in ["來源", "媒體", "sources"]):
            return {**self._empty_result(), "intent": "list_sources"}

        if any(w in text_lower for w in ["新聞", "news", "報導", "消息"]):
            category = None
            for cat in ["technology", "finance", "politics", "sports", "health", "entertainment"]:
                if cat in text_lower:
                    category = cat
            if "科技" in text_lower:
                category = "technology"
            elif "財經" in text_lower or "經濟" in text_lower or "理財" in text_lower:
                category = "finance"
            return {**self._empty_result(), "intent": "query_news", "category": category}

        return self._empty_result()
