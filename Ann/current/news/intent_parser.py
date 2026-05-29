import re
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

NEWS_KEYWORDS = [
    "新聞", "news", "摘要", "這篇", "reuters", "google news", "報導", "消息", "來源",
    "詳細說明", "詳細", "summarize", "summary", "article", "feed", "rss", "找新聞", "看新聞"
]

NEWS_SYSTEM_PROMPT = (
    "You are an intent parser for a news assistant.\n"
    "The current datetime is: {current_datetime}.\n\n"
    "Extract the user's news query intent from the message below.\n"
    "Respond ONLY with a valid JSON object. No explanation, no markdown.\n\n"
    "JSON schema:\n"
    "{\n"
    '  "intent": "query_news | summarize_article | filter_by_keyword | list_sources | none",\n'
    '  "keywords": ["string"] or [],\n'
    '  "category": "technology | finance | politics | sports | health | entertainment | general | null",\n'
    '  "source": "string or null",\n'
    '  "article_url": "string or null"\n'
    "}\n\n"
    "Rules:\n"
    "- keywords: extract relevant search terms from the user message.\n"
    "- category: infer the most relevant category (technology, finance, politics, sports, health, entertainment, general), or null if unclear.\n"
    "- source: only populate if the user explicitly names a specific source (e.g. 'reuters', 'google news').\n"
    "- article_url: only populate for summarize_article intent. Extract any HTTP/HTTPS URL found in the message.\n"
)


class NewsIntentParser:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def should_parse(self, text: str) -> bool:
        """Fast pre-filter to check if the query might be news-related."""
        text_lower = text.lower()
        if any(w in text_lower for w in NEWS_KEYWORDS):
            return True
        # Also match url
        if re.search(r"https?://\S+", text):
            return True
        return False

    def parse_intent(self, text: str) -> dict:
        """
        Sends the user text to Ollama for news intent parsing and parameter extraction.
        Returns a dict conforming to the schema.
        """
        if not self.should_parse(text):
            return {
                "intent": "none",
                "keywords": [],
                "category": None,
                "source": None,
                "article_url": None
            }

        current_datetime = datetime.now().isoformat()
        system_prompt = NEWS_SYSTEM_PROMPT.format(current_datetime=current_datetime)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        try:
            from ollama_client import OllamaClient
            client = OllamaClient(self.base_url)
            reply = client.chat(self.model, messages)
            parsed = self._clean_and_parse_json(reply)
            return parsed
        except Exception as e:
            logger.error("Failed to parse news intent using Ollama: %s", e)
            return self._regex_fallback(text)

    def _clean_and_parse_json(self, reply: str) -> dict:
        """Extracts JSON substring from the reply and parses it."""
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
                result = {k.strip().strip('"').strip("'").strip(): v for k, v in result.items()}
            
            # Normalize fields
            intent = result.get("intent", "none")
            if intent not in ["query_news", "summarize_article", "filter_by_keyword", "list_sources", "none"]:
                intent = "none"

            keywords = result.get("keywords")
            if not isinstance(keywords, list):
                keywords = []
            keywords = [str(k) for k in keywords]

            def clean_val(v):
                if isinstance(v, str):
                    v_clean = v.strip().lower()
                    if v_clean in ("null", "none", "無", "nil", ""):
                         return None
                return v

            category = clean_val(result.get("category"))
            if category not in ["technology", "finance", "politics", "sports", "health", "entertainment", "general"]:
                category = None

            source = clean_val(result.get("source"))
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
                "article_url": article_url
            }
        except Exception as e:
            logger.warning("Could not parse JSON from Ollama news reply %r: %s", reply, e)
            return {"intent": "none", "keywords": [], "category": None, "source": None, "article_url": None}

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()
        
        # Check for URLs
        url_match = re.search(r"(https?://\S+)", text)
        url = url_match.group(1) if url_match else None

        if url and any(w in text_lower for w in ["摘要", "這篇", "說明", "summary", "summarize"]):
            return {
                "intent": "summarize_article",
                "keywords": [],
                "category": None,
                "source": None,
                "article_url": url
            }

        if any(w in text_lower for w in ["來源", "媒體", "sources"]):
            return {
                "intent": "list_sources",
                "keywords": [],
                "category": None,
                "source": None,
                "article_url": None
            }

        # Check for query_news
        if any(w in text_lower for w in ["新聞", "news", "報導", "消息"]):
            # Extract basic category matching
            category = None
            for cat in ["technology", "finance", "politics", "sports", "health", "entertainment"]:
                if cat in text_lower:
                    category = cat
            if "科技" in text_lower:
                category = "technology"
            elif "財經" in text_lower or "經濟" in text_lower or "理財" in text_lower:
                category = "finance"

            return {
                "intent": "query_news",
                "keywords": [],
                "category": category,
                "source": None,
                "article_url": None
            }
            
        return {
            "intent": "none",
            "keywords": [],
            "category": None,
            "source": None,
            "article_url": None
        }
