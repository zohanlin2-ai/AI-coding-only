import sys
from pathlib import Path
sys.path.append(str(Path("current").resolve()))
sys.stdout.reconfigure(encoding='utf-8')

from news.news_manager import NewsManager

manager = NewsManager(Path("."), "http://localhost:11434", "dummy")
all_sources = manager.load_sources()
articles = []
for src in all_sources:
    url = src.get("url")
    name = src.get("name")
    region = src.get("region", "taiwan")
    feed_articles = manager.rss_fetcher.fetch_feed(url, name)
    for art in feed_articles:
        art["region"] = region
    articles.extend(feed_articles)

# Deduplicate
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

# Sort
def get_pub_date(a):
    from datetime import datetime
    try:
        return datetime.strptime(a["published"], "%Y-%m-%d %H:%M")
    except Exception:
        return datetime.min
deduped.sort(key=get_pub_date, reverse=True)

print("Total deduped articles:", len(deduped))
print("\n--- TOP 20 ARTICLES ---")
for idx, art in enumerate(deduped[:20], 1):
    print(f"{idx}. [{art.get('region')}] {art['title']} ({art['source']}) - {art['published']}")
