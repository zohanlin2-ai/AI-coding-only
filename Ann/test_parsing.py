import sys
from pathlib import Path
sys.path.append(str(Path("current").resolve()))

from news.intent_parser import NewsIntentParser

# In real world, parser connects to Ollama
# Let's inspect the regex_fallback parsing (since Ollama might be offline or returned invalid output, or regex is the fallback)
parser = NewsIntentParser("http://localhost:11434", "dummy-model")

queries = ["足球新聞", "football新聞", "科技新聞", "AI news"]

for q in queries:
    print(f"Query: {q}")
    parsed = parser._regex_fallback(q)
    print(f"Parsed Fallback: {parsed}")
