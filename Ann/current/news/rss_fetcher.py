import logging
from datetime import datetime
import feedparser

logger = logging.getLogger(__name__)

class RSSFetcher:
    def __init__(self):
        # We try to use httpx if available, else requests
        try:
            import httpx
            self.client_type = "httpx"
        except ImportError:
            self.client_type = "requests"

    def fetch_feed(self, url: str, source_name: str) -> list[dict]:
        """
        Fetches an RSS feed using requests/httpx with a 10s timeout,
        parses it with feedparser, and normalizes the entries.
        """
        logger.info("Fetching feed from URL: %s (%s)", url, source_name)
        try:
            xml_data = None
            if self.client_type == "httpx":
                import httpx
                # Using httpx with a 10-second timeout
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    xml_data = resp.text
            else:
                import requests
                # Fallback to requests with a 10-second timeout
                resp = requests.get(url, timeout=10.0, allow_redirects=True)
                resp.raise_for_status()
                xml_data = resp.text

            if not xml_data:
                logger.warning("Empty response from RSS feed: %s", url)
                return []

            parsed_feed = feedparser.parse(xml_data)
            
            articles = []
            for entry in parsed_feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                
                # Strip HTML tags from summary if any
                if summary:
                    # Clean simple HTML tags
                    summary = re_sub_html(summary)

                published = self._parse_published_date(entry)

                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "published": published,
                        "summary": summary,
                        "source": source_name
                    })

            return articles

        except Exception as e:
            logger.error("Error fetching or parsing RSS feed %s: %s", url, e)
            return []

    def _parse_published_date(self, entry) -> str:
        """Helper to extract and format published date into ISO-8601."""
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                # Convert struct_time to datetime
                dt = datetime(*parsed[:6])
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        
        # Fallback to raw string, or current time
        raw = entry.get("published") or entry.get("updated")
        if raw:
            return str(raw).strip()
        return datetime.now().strftime("%Y-%m-%d %H:%M")


def re_sub_html(html_str: str) -> str:
    """Simple regex to strip HTML tags from RSS summaries."""
    import re
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", html_str)
    # Remove excessive whitespace
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
