# News Module Specification

## 1. Purpose

This document defines the news module for a PyQt6-based AI assistant application.

The module allows users to query news through natural conversation. Ollama handles intent parsing, keyword extraction, and content summarization. The system fetches news from RSS feeds and extracts full article content on demand.

---

## 2. Scope

This specification covers:

- Conversational news queries via Ollama
- RSS feed fetching and parsing
- Full article extraction on demand
- Keyword filtering and category organization
- Short-term result caching
- RSS source management via config file

Out of scope for this version:

- Background scheduled news fetching
- Push notifications for breaking news
- User-managed RSS sources via conversation (planned for future release)

---

## 3. System Architecture

### 3.1 Component Overview

```
User Input (chat)
      ↓
Ollama Intent Parser
（extract keywords, category, source preference）
      ↓
News Fetcher
  ├── RSS Parser (feedparser)
  └── Article Extractor (newspaper3k / readability-lxml)
      ↓
Cache Layer (in-memory, 15–30 min TTL)
      ↓
Filter + Categorize
      ↓
Ollama Summarizer (on demand only)
      ↓
Response Generator (Ollama)
      ↓
Chat UI
```

### 3.2 Ollama Roles

Ollama performs three roles in this module:

**Intent Parsing**
Every news-related user message is sent to Ollama with a structured system prompt. The output is a JSON object containing the extracted query parameters.

**On-Demand Summarization**
When the user requests a summary of a specific article, Ollama receives the full article text and returns a concise summary.

**Response Generation**
After the system retrieves and filters news, Ollama generates a natural language reply presenting the results to the user.

---

## 4. Intent Recognition

### 4.1 Supported Intents

| Intent | Example Utterances |
|--------|-------------------|
| `query_news` | "Latest tech news", "Show me today's finance news", "Any news about AI?" |
| `summarize_article` | "Summarize this article for me", "What does this say?", "Give me more detail" |
| `filter_by_keyword` | "Find news about Taiwan", "Only show Python-related news" |
| `list_sources` | "What news sources do you have?", "Which media can I read from?" |
| `none` | Conversation unrelated to news |

### 4.2 Ollama Parsing Prompt

```
You are an intent parser for a news assistant.
The current datetime is: {ISO-8601 datetime}.

Extract the user's news query intent from the message below.
Respond ONLY with a valid JSON object. No explanation, no markdown.

JSON schema:
{
  "intent": "query_news | summarize_article | filter_by_keyword | list_sources | none",
  "keywords": ["string"] or [],
  "category": "technology | finance | politics | sports | health | entertainment | general | null",
  "source": "string or null",
  "article_url": "string or null"
}

Rules:
- keywords: Extract relevant search terms from the user message and dynamically expand them to include synonyms, abbreviations, related terms, leagues, or translations in both Chinese and English (limit to top 6 terms).
- category: infer the most relevant category, or null if unclear.
- source: only populate if the user explicitly names a specific source.
- article_url: only populate for summarize_article intent.
```

### 4.3 Parsed Output Example

```json
{
  "intent": "query_news",
  "keywords": ["AI", "artificial intelligence"],
  "category": "technology",
  "source": null,
  "article_url": null
}
```

---

## 5. News Sources

The system uses a **Dual-track News Sources** mechanism that separates system default sources from user custom feeds:

1. **System Default Sources**: Managed directly in the application code (`NewsManager.DEFAULT_SOURCES`). These are automatically updated when the software updates, requiring no manual intervention.
2. **User Custom Sources**: Configured in `config/news_sources.yml`. This file is reserved for user customizations and is never overwritten by system updates.

### 5.1 System Default Sources

The following sources are active by default:

* **Google News Taiwan** (general, taiwan, zh-TW)
* **Google News Technology** (technology, taiwan, zh-TW)
* **Google News Finance** (finance, taiwan, zh-TW)
* **Google News International** (general, foreign, zh-TW)
* **Google News Politics** (politics, taiwan, zh-TW)
* **Google News Sports** (sports, taiwan, zh-TW)
* **Google News Health** (health, taiwan, zh-TW)
* **Google News Entertainment** (entertainment, taiwan, zh-TW)
* **Google News International Sports** (sports, foreign, en-US)
* **Google News International Technology** (technology, foreign, en-US)
* **BBC Sport Football** (sports, foreign, en-GB)

### 5.2 User Custom Sources (`config/news_sources.yml`)

The user configuration file allows adding custom feeds, disabling default feeds, or overriding default settings by matching the source `name`:

* **Add custom feed**: Specify the `name`, `url`, `category`, `region`, and `language`.
* **Disable default feed**: Provide the matching default `name` and set `enabled: false`.
* **Override default feed**: Provide the matching default `name` and specify the fields to override (e.g. `url`).

Example configuration:
```yaml
# config/news_sources.yml
sources:
  - name: BBC Sport Football
    enabled: false  # Disables the default BBC Sports Football feed

  - name: Google News Technology
    url: https://custom-url.com/tech/rss  # Overrides the URL of default Tech feed

  - name: My Custom Tech Blog
    url: https://myblog.com/feed
    category: technology
    region: foreign
    language: en-US
```

### 5.2 Source Selection Logic

1. If the user specifies a source by name, use that source only.
2. If a category is detected, filter sources matching that category.
3. If neither is specified, query all sources and merge results.

---

## 6. News Fetching

### 6.1 RSS Parsing

- Library: `feedparser`
- Fetch all relevant RSS feeds based on source selection logic.
- Extract per article: `title`, `link`, `published`, `summary`, `source name`.
- Normalize `published` to ISO-8601 datetime.
- Sort results by `published` descending.
- Return up to **20 articles** per query before filtering.

### 6.2 Full Article Extraction

Full article extraction is performed **only when the user explicitly requests a summary** of a specific article.

- Primary library: `newspaper3k`
- Fallback library: `readability-lxml` + `beautifulsoup4`
- Extract: full article text, title, publish date, author (if available).
- Strip ads, navigation, and boilerplate content.
- If extraction fails, inform the user and provide the original link.

---

## 7. Caching

- Cache type: in-memory dictionary (per session)
- Cache key: RSS feed URL
- TTL: **20 minutes**
- On cache hit: return cached articles without re-fetching.
- On cache miss: fetch from RSS, store result with timestamp.
- Cache is cleared when the application exits.
- Full article content is not cached (fetched fresh each time on demand).

---

## 8. Filtering and Categorization

After fetching, apply filters in this order:

1. **Keyword filter:** Check the title and RSS summary for the extracted keywords. Alphanumeric/ASCII terms (e.g. "ai", "nba", "tech") match using word boundaries (`\b`) to prevent false substring matches, while Chinese/non-ASCII terms match as substrings. If the LLM is offline or keywords are unexpanded, the system falls back to static synonym expansions (`SYNONYM_EXPANSIONS`).
2. **Category filter:** Applied via source selection (Section 5.2), not post-fetch.
3. **Deduplication:** Remove articles with identical titles or URLs.
4. **Result limit:** Return up to **10 articles** to the user per query, composed of **up to 5 Taiwan articles** and **up to 5 foreign articles** (`taiwan_articles[:5] + foreign_articles[:5]`).

Categorization is handled at the source level (defined in `news_sources.yml`). No additional ML-based categorization is performed in this version.

---

## 9. Ollama Summarization

Summarization is triggered only when:

- The user asks to summarize a specific article, or
- The user selects an article from the list and requests more detail.

### 9.1 Summarization Prompt

```
You are a news summarizer. Summarize the following article concisely in 3-5 sentences.
Focus on the key facts. Do not editorialize.

Article title: {title}
Article content:
{full_article_text}
```

### 9.2 Constraints

- Maximum input tokens: limit article text to approximately 3000 tokens before sending to Ollama.
- If the article is longer, truncate from the end and append a note that content was truncated.

---

## 10. Response Format

### 10.1 Default Query Response (title + link)

```
Found 3 related news articles:

1. [Article Title 1](https://...)
   Source: Reuters | 2026-05-28 14:30

2. [Article Title 2](https://...)
   Source: Google News | 2026-05-28 13:15

3. [Article Title 3](https://...)
   Source: Google News | 2026-05-28 12:00

Would you like me to summarize one of these?
```

### 10.2 GUI Card Layout Response (PyQt6)

In GUI mode, Ann intercepts default news queries and presents them as a scrollable vertical list of up to 10 custom overlay news card widgets (`NewsCardWidget`):

- **Background**: Article's parsed `top_image` (downloaded concurrently in the background and stored locally under `scratch/news_images/`) scaled smoothly with 12px rounded corners.
- **Overlay**: Bottom-aligned black-to-transparent linear gradient for maximum text contrast.
- **Text**: White bold title, small gray source + publish time with word wrapping enabled. Titles longer than 2 lines are elided (weighted length > 76) with trailing ellipsis `...`.
- **Interaction**: Pointer cursor on hover with a glowing blue border. Left-click anywhere on the card opens the article's link in the user's default web browser. Hovering over a card displays the full news title in a custom styled tooltip (`QToolTip`).
- **Scrollbar Safety**: The scroll viewport explicitly disables horizontal scrollbars (`ScrollBarAlwaysOff`) to maintain a clean aesthetic under all screen sizes.
- **Fallback**: Solid dark linear gradient (Slate Gray to Slate Blue) if no article image is available.

### 10.3 Summarization Response

```
[Article Title 1 — Summary]

(3–5 sentence summary)

Original link: https://...
```

---

## 11. Error Handling

| Situation | Behavior |
|-----------|----------|
| RSS fetch timeout (> 10 seconds) | Skip that source, continue with others. Notify user if all sources fail. |
| RSS feed returns no articles | Inform user, suggest trying different keywords or category. |
| Article extraction fails | Inform user, provide original link for manual reading. |
| Ollama returns invalid JSON for intent | Retry once. If still invalid, treat as `none` and respond normally. |
| No articles match keyword filter | Inform user, offer to broaden the search or remove keyword filter. |
| Network unavailable | Inform user that news requires an internet connection. |

---

## 12. File Structure

```
project/
├── news/
│   ├── news_manager.py        # Orchestrates fetch, filter, cache
│   ├── rss_fetcher.py         # feedparser-based RSS fetching
│   ├── article_extractor.py   # newspaper3k / readability full-text extraction
│   ├── intent_parser.py       # Ollama JSON intent extraction
│   └── summarizer.py          # Ollama summarization
└── config/
    └── news_sources.yml       # RSS source definitions
```

---

## 13. Dependencies

| Package | Purpose |
|---------|---------|
| `feedparser` | RSS/Atom feed parsing |
| `newspaper3k` | Full article text extraction (primary) |
| `readability-lxml` | Full article text extraction (fallback) |
| `beautifulsoup4` | HTML parsing support |
| `httpx` | Async-capable HTTP requests |
| `PyYAML` | Reading `news_sources.yml` |
| `googlenewsdecoder` | Decoding Google News redirect URLs |

> Ollama communication is handled internally via `OllamaClient` (HTTP), not the `ollama` Python SDK.

---

## 14. Future Enhancements

The following features are out of scope for this version but are planned:

- **User-managed sources via conversation:** Allow users to add or remove RSS sources by describing their preference in chat.
- **Background fetching:** Periodically fetch and cache news in the background so results are available instantly.
- **Persistent cache:** Store fetched articles to disk to survive application restarts.
- **Sentiment and bias indicators:** Use Ollama to flag emotional tone or potential bias in articles.
