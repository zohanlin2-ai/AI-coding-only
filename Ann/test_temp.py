import sys
from pathlib import Path
sys.path.append(str(Path("current").resolve()))

from news.news_manager import NewsManager

# Initialize NewsManager
manager = NewsManager(Path("."), "http://localhost:11434", "dummy")

# 1. Test "足球新聞" with regex fallback parsing
# In regex fallback: category is None, keywords is ["足球"]
parsed_soccer = {
    "intent": "query_news",
    "category": None,
    "source": None,
    "keywords": ["足球"]
}
print("--- TEST: 足球新聞 ---")
res_soccer = manager.handle_intent("足球新聞", parsed_soccer)
print("Result:")
print(res_soccer)
print("Articles length:", len(manager.last_fetched_articles))
for a in manager.last_fetched_articles:
    print(f"- [{a.get('region')}] {a.get('title')} ({a.get('source')})")

# 2. Test "科技新聞" with category="technology", keywords=[]
parsed_tech = {
    "intent": "query_news",
    "category": "technology",
    "source": None,
    "keywords": []
}
print("\n--- TEST: 科技新聞 ---")
res_tech = manager.handle_intent("科技新聞", parsed_tech)
print("Result:")
print(res_tech)
print("Articles length:", len(manager.last_fetched_articles))
for a in manager.last_fetched_articles:
    print(f"- [{a.get('region')}] {a.get('title')} ({a.get('source')})")
