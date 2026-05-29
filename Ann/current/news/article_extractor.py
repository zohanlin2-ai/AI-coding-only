import logging

logger = logging.getLogger(__name__)

class ArticleExtractor:
    def __init__(self):
        # We try to use httpx or requests
        try:
            import httpx
            self.client_type = "httpx"
        except ImportError:
            self.client_type = "requests"

    def extract(self, url: str) -> dict:
        """
        Extracts full article content and metadata from the given URL.
        Returns a dict:
        {
            "success": bool,
            "title": str or None,
            "text": str or None,
            "publish_date": str or None,
            "authors": list of str or None,
            "source_url": str,
            "top_image": str or None
        }
        """
        logger.info("Extracting article from URL: %s", url)
        
        # Primary: newspaper3k
        try:
            from newspaper import Article
            logger.info("Using newspaper3k for extraction")
            article = Article(url, keep_article_html=False)
            article.download()
            article.parse()
            
            title = article.title
            text = article.text
            
            publish_date_str = None
            if article.publish_date:
                publish_date_str = article.publish_date.strftime("%Y-%m-%d %H:%M")
                
            top_image = getattr(article, "top_image", None) or None

            if title and text and len(text.strip()) > 100:
                logger.info("Successfully extracted article using newspaper3k: %s", title)
                return {
                    "success": True,
                    "title": title,
                    "text": text,
                    "publish_date": publish_date_str,
                    "authors": article.authors,
                    "source_url": url,
                    "top_image": top_image
                }
        except Exception as e:
            logger.warning("newspaper3k extraction failed for %s: %s. Trying fallback...", url, e)

        # Fallback: readability-lxml + beautifulsoup4
        try:
            logger.info("Using readability-lxml fallback for extraction")
            html_content = None
            if self.client_type == "httpx":
                import httpx
                with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    html_content = resp.text
            else:
                import requests
                resp = requests.get(url, timeout=15.0, allow_redirects=True)
                resp.raise_for_status()
                html_content = resp.text

            if not html_content:
                raise ValueError("Received empty HTML content from page")

            from readability import Document
            from bs4 import BeautifulSoup

            doc = Document(html_content)
            title = doc.title()
            summary_html = doc.summary()
            
            soup = BeautifulSoup(summary_html, "html.parser")
            # Extract text, separating paragraphs by newlines
            text = soup.get_text(separator="\n").strip()
            
            # Clean up excessive newlines
            import re
            text = re.sub(r"\n\s*\n+", "\n\n", text)

            og_image = None
            try:
                soup_full = BeautifulSoup(html_content, "html.parser")
                meta_og = soup_full.find("meta", property="og:image")
                if meta_og and meta_og.get("content"):
                    og_image = meta_og.get("content")
                else:
                    meta_tw = soup_full.find("meta", name="twitter:image")
                    if meta_tw and meta_tw.get("content"):
                        og_image = meta_tw.get("content")
            except Exception as ex:
                logger.debug("Failed to extract fallback image og:image: %s", ex)

            if title and text and len(text.strip()) > 50:
                logger.info("Successfully extracted article using readability-lxml: %s", title)
                return {
                    "success": True,
                    "title": title,
                    "text": text,
                    "publish_date": None,
                    "authors": [],
                    "source_url": url,
                    "top_image": og_image
                }
            else:
                raise ValueError("Extracted text too short or empty")

        except Exception as e:
            logger.error("All article extraction methods failed for %s: %s", url, e)
            return {
                "success": False,
                "title": None,
                "text": None,
                "publish_date": None,
                "authors": [],
                "source_url": url,
                "top_image": None
            }
