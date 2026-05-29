import sys
from pathlib import Path
import pytest
import yaml
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Add parent path to imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from news.intent_parser import NewsIntentParser
from news.rss_fetcher import RSSFetcher, re_sub_html
from news.article_extractor import ArticleExtractor
from news.summarizer import NewsSummarizer
from news.news_manager import NewsManager


def test_html_stripping():
    html_text = "<p>This is <b>bold</b> text.</p>"
    assert re_sub_html(html_text) == "This is bold text."


def test_news_intent_parser_should_parse():
    parser = NewsIntentParser("http://localhost:11434", "test-model")
    assert parser.should_parse("今天有什麼新聞嗎？") is True
    assert parser.should_parse("幫我摘要這篇報導") is True
    assert parser.should_parse("reuters news") is True
    assert parser.should_parse("https://news.google.com/test") is True
    assert parser.should_parse("你好，請問你是誰？") is False


def test_news_intent_parser_regex_fallback():
    parser = NewsIntentParser("http://localhost:11434", "test-model")
    
    # List sources intent
    parsed = parser._regex_fallback("有什麼新聞來源？")
    assert parsed["intent"] == "list_sources"

    # Summarize article intent
    parsed = parser._regex_fallback("幫我摘要這篇 https://example.com/article1")
    assert parsed["intent"] == "summarize_article"
    assert parsed["article_url"] == "https://example.com/article1"

    # Query news intent
    parsed = parser._regex_fallback("我想看科技新聞")
    assert parsed["intent"] == "query_news"
    assert parsed["category"] == "technology"

    # Query news general intent
    parsed = parser._regex_fallback("今天的新聞報導有哪些")
    assert parsed["intent"] == "query_news"
    assert parsed["category"] is None


def test_news_intent_parser_key_normalization():
    parser = NewsIntentParser("http://localhost:11434", "test-model")
    
    # Test case where keys have leading whitespace/newlines and nested quotes
    reply_with_weird_keys = '{\n  "\\n  \\"intent\\"": "query_news",\n  "  \\"keywords\\"": ["AI"],\n  "category": "technology"\n}'
    parsed = parser._clean_and_parse_json(reply_with_weird_keys)
    assert parsed["intent"] == "query_news"
    assert parsed["keywords"] == ["AI"]
    assert parsed["category"] == "technology"


@patch("news.rss_fetcher.feedparser.parse")
def test_rss_fetcher_normalize(mock_parse):
    # Setup mock parsed feed
    mock_feed = MagicMock()
    mock_entry1 = {
        "title": "AI News 1",
        "link": "https://example.com/ai1",
        "summary": "<p>AI is taking over.</p>",
        "published_parsed": (2026, 5, 29, 10, 0, 0, 4, 149, 0)
    }
    mock_entry2 = {
        "title": "Sports News 1",
        "link": "https://example.com/sports1",
        "summary": "Team wins!",
        "published": "2026-05-29 09:30"
    }
    mock_feed.entries = [mock_entry1, mock_entry2]
    mock_parse.return_value = mock_feed

    fetcher = RSSFetcher()
    # Mock network call to return mock xml
    with patch.object(fetcher, "client_type", "mock"):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<xml></xml>"
            mock_get.return_value = mock_resp
            
            articles = fetcher.fetch_feed("https://example.com/rss", "Mock Source")
            
            assert len(articles) == 2
            assert articles[0]["title"] == "AI News 1"
            assert articles[0]["link"] == "https://example.com/ai1"
            assert articles[0]["summary"] == "AI is taking over."
            assert articles[0]["published"] == "2026-05-29 10:00"
            assert articles[0]["source"] == "Mock Source"

            assert articles[1]["title"] == "Sports News 1"
            assert articles[1]["published"] == "2026-05-29 09:30"


@patch("newspaper.Article")
def test_article_extractor_newspaper3k(mock_article):
    # Mock newspaper3k Article behavior
    mock_inst = MagicMock()
    mock_inst.title = "Test Article Title"
    mock_inst.text = "This is a very long text representing the parsed news article content extracted by newspaper3k library that exceeds one hundred characters."
    mock_inst.publish_date = datetime(2026, 5, 29, 10, 15)
    mock_inst.authors = ["Jane Doe"]
    mock_article.return_value = mock_inst

    extractor = ArticleExtractor()
    res = extractor.extract("https://example.com/article")
    
    assert res["success"] is True
    assert res["title"] == "Test Article Title"
    assert "extracted by newspaper3k" in res["text"]
    assert res["publish_date"] == "2026-05-29 10:15"
    assert res["authors"] == ["Jane Doe"]


@patch("ollama_client.OllamaClient.chat")
def test_news_summarizer_truncation(mock_chat):
    mock_chat.return_value = "這是文章摘要。"
    summarizer = NewsSummarizer("http://localhost:11434", "test-model")
    
    # Verify non-truncated call
    res = summarizer.summarize("Title", "Short content")
    assert res == "這是文章摘要。"
    
    # Verify truncated call
    long_content = "A" * 12000
    res = summarizer.summarize("Title", long_content)
    assert res == "這是文章摘要。"
    assert mock_chat.call_count == 2
    # Check that second call prompt contained the truncation notice
    sent_prompt = mock_chat.call_args[0][1][0]["content"]
    assert "[注意：文章內容過長，已截斷後半部]" in sent_prompt


def test_news_manager_caching_and_filtering(tmp_path):
    # Setup directories
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    sources_file = config_dir / "news_sources.yml"
    
    sources_data = {
        "sources": [
            {"name": "Tech News", "url": "https://tech.com/rss", "category": "technology", "language": "zh-TW"},
            {"name": "General News", "url": "https://general.com/rss", "category": "general", "language": "zh-TW"}
        ]
    }
    with open(sources_file, "w", encoding="utf-8") as f:
        yaml.dump(sources_data, f)

    manager = NewsManager(tmp_path, "http://localhost:11434", "test-model")
    
    # Mock RSSFetcher
    manager.rss_fetcher = MagicMock()
    tech_articles = [
        {"title": "AI Breakout", "link": "https://tech.com/ai", "published": "2026-05-29 11:00", "summary": "AI is fast", "source": "Tech News"},
        {"title": "Python 3.12", "link": "https://tech.com/py", "published": "2026-05-29 10:00", "summary": "Python release", "source": "Tech News"}
    ]
    gen_articles = [
        {"title": "World Peace", "link": "https://general.com/peace", "published": "2026-05-29 10:30", "summary": "Peace achieved", "source": "General News"}
    ]
    
    def side_effect(url, name):
        if "tech" in url:
            return tech_articles
        return gen_articles
    
    manager.rss_fetcher.fetch_feed.side_effect = side_effect

    # Query category technology
    parsed = {
        "intent": "query_news",
        "category": "technology",
        "source": None,
        "keywords": []
    }
    
    res = manager.handle_intent("幫我查科技新聞", parsed)
    assert "AI Breakout" in res
    assert "Python 3.12" in res
    assert "World Peace" not in res
    assert len(manager.last_fetched_articles) == 2

    # Check cache is set
    assert "https://tech.com/rss" in manager.cache
    assert manager.cache["https://tech.com/rss"][1] == tech_articles

    # Query with keywords
    parsed_kw = {
        "intent": "query_news",
        "category": None,
        "source": None,
        "keywords": ["peace"]
    }
    res_kw = manager.handle_intent("有關於 peace 的新聞嗎", parsed_kw)
    assert "World Peace" in res_kw
    assert "AI Breakout" not in res_kw
    assert len(manager.last_fetched_articles) == 1

    # Match article from history (index)
    url, title = manager._match_article_from_history("摘要第一篇", [])
    assert url == "https://general.com/peace"
    assert title == "World Peace"
