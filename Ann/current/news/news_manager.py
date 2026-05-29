import os
import re
import yaml
import logging
from pathlib import Path
from datetime import datetime, timedelta

from news.intent_parser import NewsIntentParser
from news.rss_fetcher import RSSFetcher
from news.article_extractor import ArticleExtractor
from news.summarizer import NewsSummarizer

logger = logging.getLogger(__name__)


class NewsManager:
    def __init__(self, base_dir: Path, base_url: str, model: str):
        self.base_dir = base_dir
        self.config_path = base_dir / "config" / "news_sources.yml"
        self.base_url = base_url
        self.model = model

        # Sub-modules
        self.intent_parser = NewsIntentParser(base_url, model)
        self.rss_fetcher = RSSFetcher()
        self.extractor = ArticleExtractor()
        self.summarizer = NewsSummarizer(base_url, model)

        # Caching
        # Format: { feed_url: (timestamp, list_of_articles) }
        self.cache = {}
        self.cache_ttl = timedelta(minutes=20)

        # Session memory
        self.last_fetched_articles = []

    def load_sources(self) -> list[dict]:
        """Loads news sources from config/news_sources.yml."""
        if not self.config_path.exists():
            self._write_default_sources()
        else:
            # Self-repair: detect and overwrite outdated broken feeds URLs
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "feeds.reuters.com" in content or "CAAqJggKIiBDQkFTRWdvSUwyMHZNR" in content:
                    logger.info("Outdated news sources config detected. Updating to modern feeds.")
                    self._write_default_sources()
            except Exception:
                pass

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("sources", [])
        except Exception as e:
            logger.error("Failed to load news sources config: %s", e)
            return []

    def _write_default_sources(self) -> None:
        """Writes default news sources configuration to config/news_sources.yml."""
        default_yaml = """sources:
  - name: Google News 台灣
    url: https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant
    category: general
    language: zh-TW

  - name: Google News 科技
    url: https://news.google.com/news/rss/headlines/section/topic/TECHNOLOGY?hl=zh-TW&gl=TW&ceid=TW:zh-Hant
    category: technology
    language: zh-TW

  - name: Google News 財經
    url: https://news.google.com/news/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant
    category: finance
    language: zh-TW

  - name: Google News 國際
    url: https://news.google.com/news/rss/headlines/section/topic/WORLD?hl=zh-TW&gl=TW&ceid=TW:zh-Hant
    category: general
    language: zh-TW
"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(default_yaml, encoding="utf-8")
            logger.info("Created default news sources config at %s", self.config_path)
        except Exception as e:
            logger.error("Failed to write default news sources config: %s", e)

    def handle_intent(self, user_input: str, parsed: dict) -> str:
        """
        Orchestrates flow based on parsed intent.
        Returns the formatted response string.
        """
        intent = parsed.get("intent", "none")
        
        if intent == "list_sources":
            sources = self.load_sources()
            if not sources:
                return "目前沒有設定任何新聞來源。"
            
            lines = ["目前支援的新聞來源如下：\n"]
            for s in sources:
                lang_str = f" ({s.get('language')})" if s.get("language") else ""
                lines.append(f"- **{s.get('name')}** (類別: {s.get('category')}){lang_str}")
            return "\n".join(lines)

        elif intent in ("query_news", "filter_by_keyword"):
            category = parsed.get("category")
            source_pref = parsed.get("source")
            keywords = parsed.get("keywords") or []

            # 1. Source selection logic
            all_sources = self.load_sources()
            selected_sources = []
            
            if source_pref:
                # Filter by name matching
                source_pref_lower = source_pref.lower()
                selected_sources = [s for s in all_sources if source_pref_lower in s.get("name", "").lower()]
            
            if not selected_sources and category:
                # Filter by category
                category_lower = category.lower()
                selected_sources = [s for s in all_sources if s.get("category", "").lower() == category_lower]

            if not selected_sources:
                # Fallback to all sources
                selected_sources = all_sources

            if not selected_sources:
                return "無法取得新聞，目前未設定任何新聞來源。"

            # 2. Fetch and Cache
            articles = []
            now = datetime.now()
            
            for src in selected_sources:
                url = src.get("url")
                name = src.get("name")
                if not url:
                    continue

                cached_data = self.cache.get(url)
                if cached_data and (now - cached_data[0]) < self.cache_ttl:
                    logger.info("Cache hit for feed: %s", url)
                    feed_articles = cached_data[1]
                else:
                    logger.info("Cache miss for feed: %s. Fetching...", url)
                    feed_articles = self.rss_fetcher.fetch_feed(url, name)
                    self.cache[url] = (now, feed_articles)
                
                articles.extend(feed_articles)

            if not articles:
                return "抱歉，目前無法從選定的來源取得任何新聞報導。"

            # 3. Deduplication (by title or link)
            seen_titles = set()
            seen_links = set()
            deduped = []
            for art in articles:
                title = art["title"].lower().strip()
                link = art["link"].lower().strip()
                if title not in seen_titles and link not in seen_links:
                    seen_titles.add(title)
                    seen_links.add(link)
                    deduped.append(art)

            # Sort by published date descending (newest first)
            # Standard published format: YYYY-MM-DD HH:MM
            def get_pub_date(a):
                try:
                    return datetime.strptime(a["published"], "%Y-%m-%d %H:%M")
                except Exception:
                    return datetime.min

            deduped.sort(key=get_pub_date, reverse=True)

            # 4. Keyword Filtering
            filtered = []
            if keywords:
                # Filter keywords case-insensitive
                kw_lowers = [kw.lower() for kw in keywords if kw]
                for art in deduped:
                    title_lower = art["title"].lower()
                    summary_lower = art["summary"].lower()
                    if any(kw in title_lower or kw in summary_lower for kw in kw_lowers):
                        filtered.append(art)
            else:
                filtered = deduped

            if not filtered:
                if keywords:
                    return f"找不到與關鍵字「{', '.join(keywords)}」相關的新聞。您可以嘗試換個關鍵字或瀏覽其他類別。"
                return "目前沒有合適的新聞報導。"

            # Limit results to 10
            final_articles = filtered[:10]
            self.last_fetched_articles = final_articles

            # Fetch article images in parallel
            self.fetch_article_images(final_articles)

            # 5. Format response
            lines = [f"找到 {len(final_articles)} 則相關新聞：\n"]
            for idx, art in enumerate(final_articles, 1):
                lines.append(f"{idx}. [{art['title']}]({art['link']})")
                lines.append(f"   來源：{art['source']}｜{art['published']}\n")
            lines.append("想要我摘要某篇嗎？（例如：『摘要第一篇』或提供文章網址）")
            
            return "\n".join(lines)

        elif intent == "summarize_article":
            article_url = parsed.get("article_url")
            keywords = parsed.get("keywords") or []
            
            # Match last fetched articles if URL is not direct
            title = None
            if not article_url:
                article_url, title = self._match_article_from_history(user_input, keywords)

            if not article_url:
                return "請提供具體的新聞連結，或指定要摘要上一輪搜尋結果中的哪篇新聞（例如：『摘要第一篇』）。"

            # Fetch full text
            extracted = self.extractor.extract(article_url)
            if not extracted["success"]:
                return f"抱歉，我無法擷取該網頁的全文內容。您可以點擊原連結直接閱讀：\n{article_url}"

            # Summarize
            article_title = extracted["title"] or title or "未命名文章"
            article_text = extracted["text"]
            
            try:
                summary = self.summarizer.summarize(article_title, article_text)
                response = (
                    f"【{article_title}摘要】\n\n"
                    f"{summary}\n\n"
                    f"原文連結：{article_url}"
                )
                return response
            except Exception as e:
                return f"摘要生成失敗：{e}\n\n您可以點擊原連結直接閱讀：\n{article_url}"

        return "未偵測到新聞意圖。"

    def _match_article_from_history(self, user_input: str, keywords: list[str]) -> tuple[str | None, str | None]:
        """Matches index or keyword against last fetched articles list."""
        if not self.last_fetched_articles:
            return None, None

        # 1. Match index digit
        match_index = re.search(r"(?:第)?(\d+)(?:篇|個)?", user_input)
        if match_index:
            idx = int(match_index.group(1))
            if 1 <= idx <= len(self.last_fetched_articles):
                art = self.last_fetched_articles[idx - 1]
                return art["link"], art["title"]

        # 2. Match Chinese word index
        word_map = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, 
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "首": 1, "最後": len(self.last_fetched_articles)
        }
        for w, idx in word_map.items():
            if f"第{w}" in user_input or f"摘要{w}" in user_input or (w == "最後" and "最後一篇" in user_input):
                if 1 <= idx <= len(self.last_fetched_articles):
                    art = self.last_fetched_articles[idx - 1]
                    return art["link"], art["title"]

        # 3. Match by keyword in title
        kw_lowers = [kw.lower() for kw in keywords if kw]
        if kw_lowers:
            for art in self.last_fetched_articles:
                title_lower = art["title"].lower()
                if any(kw in title_lower for kw in kw_lowers):
                    return art["link"], art["title"]

        return None, None

    def fetch_article_images(self, articles: list[dict]) -> None:
        """
        Scrapes article web pages in parallel to extract top_image URLs and download them locally.
        Saves downloaded images to scratch/news_images/ and sets article['local_image_path'].

        Uses wait() instead of as_completed() with a timeout so that slow or
        unavailable articles are skipped gracefully rather than raising a
        TimeoutError that aborts the entire batch.
        """
        import urllib.parse
        import hashlib
        import httpx
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

        # Ensure directory exists
        img_dir = self.base_dir / "scratch" / "news_images"
        try:
            img_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("Failed to create news_images directory: %s", e)
            return

        # Simple cleanup of old files in scratch/news_images (older than 2 days)
        try:
            now = datetime.now()
            for f in img_dir.iterdir():
                if f.is_file():
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if now - mtime > timedelta(days=2):
                        f.unlink()
        except Exception as e:
            logger.debug("Failed to clean up old news images: %s", e)

        def process_article(art: dict):
            url = art.get("link")
            if not url:
                art["top_image"] = None
                art["local_image_path"] = None
                return

            # If it's a Google News redirect URL, decode it to get the real destination URL
            if url.startswith("https://news.google.com/rss/articles/") or url.startswith("https://news.google.com/articles/"):
                try:
                    from googlenewsdecoder import new_decoderv1
                    res = new_decoderv1(url)
                    if res.get("status") and res.get("decoded_url"):
                        url = res["decoded_url"]
                        art["link"] = url  # Update to the real URL for extraction and interaction
                except Exception as e:
                    logger.warning("Failed to decode Google News URL %s: %s", url, e)

            # Generate stable filename based on URL hash
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()

            # Extract page metadata to find the top image
            try:
                extracted = self.extractor.extract(url)
                top_image = extracted.get("top_image")
            except Exception as e:
                logger.warning("Failed to extract page for image %s: %s", url, e)
                top_image = None

            art["top_image"] = top_image
            art["local_image_path"] = None

            if not top_image:
                return

            # Determine extension
            parsed_img_url = urllib.parse.urlparse(top_image)
            path = parsed_img_url.path.lower()
            ext = ".png"
            if path.endswith(".jpg") or path.endswith(".jpeg"):
                ext = ".jpg"
            elif path.endswith(".webp"):
                ext = ".webp"
            elif path.endswith(".gif"):
                ext = ".gif"
            elif path.endswith(".bmp"):
                ext = ".bmp"

            local_path = img_dir / f"{url_hash}{ext}"
            if local_path.exists():
                art["local_image_path"] = str(local_path)
                return

            # Download the image
            try:
                if self.extractor.client_type == "httpx":
                    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                        resp = client.get(top_image, headers=headers)
                        resp.raise_for_status()
                        img_data = resp.content
                else:
                    import requests
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    resp = requests.get(top_image, headers=headers, timeout=10.0, allow_redirects=True)
                    resp.raise_for_status()
                    img_data = resp.content

                if img_data:
                    local_path.write_bytes(img_data)
                    art["local_image_path"] = str(local_path)
                    logger.info("Successfully downloaded image for %s -> %s", url, local_path)
            except Exception as e:
                logger.warning("Failed to download image %s: %s", top_image, e)

        # Run process_article in parallel.
        # Use wait() with a generous per-batch timeout so that slow articles are
        # skipped gracefully rather than raising TimeoutError for the whole batch.
        # Each article may take up to ~15 s (decode + extract + download), so
        # allow 60 s total for 10 articles running concurrently.
        BATCH_TIMEOUT = 60.0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_article, art): art for art in articles}
            done, pending = wait(futures, timeout=BATCH_TIMEOUT)

            # Collect results from completed futures
            for fut in done:
                try:
                    fut.result()
                except Exception as e:
                    logger.error("Error processing article image in thread: %s", e)

            # Log any articles that did not finish in time (they keep running
            # in the background but we won't block the UI waiting for them)
            if pending:
                logger.warning(
                    "%d article image(s) did not finish within %.0f s and will be skipped.",
                    len(pending), BATCH_TIMEOUT
                )
                for fut in pending:
                    fut.cancel()
