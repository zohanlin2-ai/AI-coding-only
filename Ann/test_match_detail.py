import sys
from pathlib import Path
sys.path.append(str(Path("current").resolve()))
sys.stdout.reconfigure(encoding='utf-8')

from news.news_manager import NewsManager

manager = NewsManager(Path("."), "http://localhost:11434", "dummy")

parsed_soccer = {
    "intent": "query_news",
    "category": None,
    "source": None,
    "keywords": ["足球"]
}

# Run the normal query
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

# Fallback filtering logic
cleaned_keywords = ["足球"]
search_terms = []
for kw in cleaned_keywords:
    kw_lower = kw.lower().strip()
    search_terms.append(kw_lower)
    # Synonym expansions
    from news.news_manager import SYNONYM_EXPANSIONS
    if kw_lower in SYNONYM_EXPANSIONS:
        search_terms.extend(SYNONYM_EXPANSIONS[kw_lower])

search_terms = list(set(search_terms))
print("Search terms:", search_terms)

for art in deduped:
    title_lower = art["title"].lower()
    summary_lower = art["summary"].lower()
    matched = [term for term in search_terms if term in title_lower or term in summary_lower]
    if matched:
        print(f"\nMATCHED: [{art.get('region')}] {art['title']}")
        print(f"Matched terms: {matched}")
        print(f"Summary: {art['summary'][:150]}")
