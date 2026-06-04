# AI Memory System Design Document (v2)

## 1. Design Goals

This document describes a memory management system designed for small local LLMs, such as 4B-class models.

Core goals:

- Allow the AI to remember user preferences, project context, recent tasks, and important facts.
- Avoid loading all memories on every turn, reducing prompt length and response latency.
- Support short-term and long-term memory.
- Support automatic extraction, retrieval, organization, merging, and deletion.
- Keep the user in control: allow viewing, editing, deleting, and disabling memories.
- Store data in JSON format for easy local implementation and debugging.

---

## 2. Core Principles

### 2.1 Never Load All Memories at Once

Loading all memories before every response causes the local 4B model to slow down progressively as memory grows.

The improved principle is:

```text
User input
  -> Generate query keywords or embedding
  -> Search for relevant memories
  -> Load only top 3 to top 10 memories
  -> Build prompt
  -> LLM responds
```

Only memories relevant to the current question enter the prompt.

### 2.2 Organize Memories in Small Batches

Never send all memories to the LLM for organization at once. As memory grows, this causes:

- Very slow responses
- Context window overflow
- Malformed JSON output
- Accidental deletion or merging of important data

The improved approach uses small-batch organization:

- Only organize memories within the same category
- Only organize memories with similar keywords or embeddings
- Maximum 20 to 50 entries per batch
- Write results to a temp file first; replace the original only after validation

### 2.3 Users Must Be Able to Control Memory

The memory system should not be a black box. Users should be able to:

- View what the AI currently remembers
- Manually add memories
- Edit memories
- Delete memories
- Pause memory functionality
- Tell the AI "don't remember this"
- Tell the AI "please remember this"

---

## 3. Memory Unit Format

Each memory entry is called a memory unit.

```json
{
  "id": "M.1",
  "created_at": "2026-06-03T14:20:00+08:00",
  "updated_at": "2026-06-03T14:20:00+08:00",
  "category": "project",
  "keywords": ["local LLM", "memory", "4B"],
  "summary": "User is building a local 4B LLM chat application and wants to add a memory feature.",
  "details": "The main issue is slow model response time (10+ seconds per turn), so the memory system must avoid adding too much to the prompt length.",
  "confidence": 0.85,
  "status": "active",
  "source": "conversation"
}
```

### 3.1 Field Descriptions

| Field | Description | Notes |
|-------|-------------|-------|
| `id` | Memory serial number | Format: `M.N` |
| `created_at` | Creation timestamp | ISO 8601 format |
| `updated_at` | Last updated timestamp | ISO 8601 format |
| `category` | Memory type | Used for retrieval and organization |
| `keywords` | Keyword tags | 1 to 5 keywords |
| `summary` | Short summary | Used in prompt by default |
| `details` | Full detail | Loaded only when needed (see Section 3.3) |
| `confidence` | Confidence score | 0.0 to 1.0 (see Section 3.2) |
| `status` | Entry status | `active`, `outdated`, `deleted` |
| `source` | Origin of the memory | `conversation`, `manual`, `system` |

### 3.2 Confidence Score Rules

The confidence score is assigned by the AI at extraction time, following these rules:

| Situation | Confidence |
|-----------|------------|
| User explicitly states a fact ("My name is...") | 0.90 – 1.00 |
| Fact clearly implied by context | 0.70 – 0.89 |
| AI inference or assumption | 0.40 – 0.69 |
| Uncertain or speculative | Below 0.40 — do not save |
| User manually adds a memory | 1.00 |
| User says "don't remember this" | Do not write to memory |

Memories with `confidence` below 0.40 should not be saved. Memories below 0.60 should be flagged as low-confidence and deprioritized during retrieval.

### 3.3 Separating `summary` and `details`

`summary` and `details` are stored in the same JSON file, but `details` is not loaded into the prompt by default. During retrieval, only `summary` is returned. `details` is fetched separately only when the current question clearly requires it (e.g., the user asks for specifics about a past project).

This keeps prompt size small even as the number of memories grows.

### 3.4 Recommended Categories

```text
profile      User identity and long-term background
preference   Preferences, habits, tone
project      Project information
todo         To-do items and commitments
event        Recent events
skill        Skills the user is learning or familiar with
correction   Things the user has corrected the AI about
system       AI system settings or interaction rules
```

---

## 4. Short-Term and Long-Term Memory

Short-term and long-term classification is determined automatically by `created_at`. No additional field is required.

| Type | Condition |
|------|-----------|
| Short-term memory | `created_at` within the last 3 days |
| Long-term memory | `created_at` more than 3 days ago |

Usage guidelines:

- Short-term memory: retrieved with higher priority; usually more relevant to the current conversation.
- Long-term memory: only loaded when relevant to the current question.
- Outdated or conflicting memories: mark as `outdated` rather than deleting immediately.

---

## 5. File Structure

```text
memory/
  index.json
  memories/
    2026-06-03_memory.json
    2026-06-04_memory.json
  backup/
  trash/
```

### 5.1 Daily Memory File

Filename format:

```text
YYYY-MM-DD_memory.json
```

A new file is created automatically when the first memory of the day is written. Empty files are never created in advance.

Content format:

```json
{
  "memories": [
    {
      "id": "M.1",
      "created_at": "2026-06-03T14:20:00+08:00",
      "updated_at": "2026-06-03T14:20:00+08:00",
      "category": "project",
      "keywords": ["local LLM", "memory"],
      "summary": "User is building a local LLM memory system.",
      "details": "The system needs to support short-term, long-term, retrieval, organization, and user control.",
      "confidence": 0.9,
      "status": "active",
      "source": "conversation"
    }
  ]
}
```

### 5.2 index.json

```json
{
  "schema_version": 1,
  "last_organized": "2026-06-03T14:30:00+08:00",
  "needs_organization": false,
  "total_size_bytes": 102400,
  "total_memories": 243,
  "active_memories": 220,
  "outdated_memories": 18,
  "deleted_memories": 5,
  "files": [
    {
      "filename": "2026-06-03_memory.json",
      "size_bytes": 12800,
      "memory_count": 30,
      "short_term": true
    }
  ]
}
```

---

## 6. Conversation Flow

### 6.1 Memory Read Flow

Before every AI response, the system reads a small set of relevant memories from disk. The read flow is as follows:

```text
User sends message
  -> Step 1: Extract search keywords from user input
  -> Step 2: Read index.json to identify which daily files exist
  -> Step 3: Determine which files to scan
             - Always scan today's file (short-term, highest priority)
             - Scan files from the last 3 days (short-term)
             - Scan older files only if short-term results are insufficient
  -> Step 4: Within each scanned file, filter entries where:
             - status == "active"
             - keywords overlap with the search keywords
             - confidence >= 0.60
  -> Step 5: Score and rank all matching entries
  -> Step 6: Select top 3 to 10 entries
  -> Step 7: For each selected entry, load summary only
             (load details only if the question clearly requires it)
  -> Step 8: Pass selected entries to prompt builder
```

#### Which files to read

| Situation | Files to scan |
|-----------|---------------|
| Short-term results >= 5 | Today + last 3 days only |
| Short-term results < 5 | Extend to long-term files until top 5 is reached |
| User asks about a specific past topic | Search all files regardless of date |
| User asks about current preferences or identity | Prioritize `profile` and `preference` categories across all files |

#### What gets loaded into the prompt

Only `summary` is loaded by default. `details` is fetched as a separate read operation and only when the user's question clearly requires deeper context, for example:

- "What were the exact requirements I gave you last week?"
- "Can you remind me of all the details about my project?"

For general conversation, `summary` alone is sufficient and keeps prompt size small.

### 6.2 Two-Phase Memory Extraction

Memory extraction happens in two phases to capture information as early as possible:

```text
[Phase 1 — On User Input]
User sends message
  -> Extract facts from the user's message (name, preferences, project info, etc.)
  -> Write to today's memory file immediately (background)

[Phase 2 — After AI Response]
AI finishes responding
  -> Extract conclusions, commitments, and context from the full turn
  -> Deduplicate against Phase 1 extractions
  -> Write any new entries to today's memory file (background)
  -> Update index.json
```

Splitting extraction into two phases ensures that important facts stated by the user are captured even if the AI response is slow or the session ends unexpectedly.

### 6.3 Full Conversation Flow

```text
User input
  -> [Read] Extract search keywords
  -> [Read] Scan index.json → identify relevant files
  -> [Read] Filter and rank matching memories
  -> [Read] Load summaries of top memories
  -> [Phase 1 Write] Extract user-stated facts (background)
  -> Build prompt with memories + conversation history
  -> LLM responds
  -> [Phase 2 Write] Extract turn conclusions (background)
  -> Write new memories to today's file
  -> Update index.json
```

### 6.4 Prompt Structure

```text
[System Prompt]
You are a local AI assistant.

[Relevant Memory]
M.12 [project, local LLM] User is building a local 4B LLM chat application.
M.18 [preference, concise] User prefers direct, actionable suggestions.

[Current Conversation History]
user: ...
assistant: ...

[Current Question]
user: ...
```

Guidelines:

- Load a maximum of 3 to 10 memories per turn.
- Always use `summary`; load `details` only when the question clearly requires it (see Section 6.1).
- Apply the token budget defined in Section 14.

---

## 7. Memory Retrieval Strategy

### 7.1 MVP: Keyword Search

No embedding required. Simple keyword matching:

```text
1. Extract keywords from user input.
2. Search memories for keyword overlap.
3. Sort by category match, recency, and keyword overlap count.
4. Return top 3 to top 10.
```

### 7.2 Advanced: Embedding Search

```text
1. Build embeddings for all memory summaries.
2. Build an embedding for the user input.
3. Rank memories by cosine similarity.
4. Combine with recency, category, and status for final ranking.
```

Recommended scoring formula:

```text
score =
  semantic_similarity * 0.55
  + keyword_match      * 0.25
  + recency_score      * 0.15
  + confidence         * 0.05
```

---

## 8. Memory Write Flow

After the AI responds, memory extraction runs in the background so the user does not wait.

```text
AI finishes responding
  -> Background task starts
  -> Analyze turn for memorable information
  -> Output JSON
  -> Validate schema
  -> Acquire file lock
  -> Write to today's memory file
  -> Release file lock
  -> Update index.json
```

### 8.1 Extraction Prompt

```text
Analyze the following conversation and determine whether it contains information worth remembering.

Save only the following types:
- Explicit user preferences
- User personal background
- Ongoing projects
- To-do items or commitments
- Corrections the user made to the AI
- Context that would help with future responses

Do NOT save:
- One-off small talk
- Sensitive personal data unless the user explicitly asks
- Uncertain or speculative inferences (confidence below 0.40)

Output a JSON array only. No other text.

Each entry format:
{
  "category": "...",
  "keywords": ["..."],
  "summary": "...",
  "details": "...",
  "confidence": 0.0 to 1.0
}

[Conversation]
...
```

---

## 9. Memory Organization Flow

### 9.1 Trigger Conditions

| Trigger | Description |
|---------|-------------|
| Program startup | Check for incomplete organization; run if needed |
| Hourly boundary | If a clock-hour boundary was crossed between two minute-checks, trigger organization |
| Memory count threshold | e.g., trigger after 30 new entries are added |
| Normal shutdown | Run a lightweight organization pass before exit |

### 9.2 Hourly Trigger Logic

```python
import time
from datetime import datetime

last_check_hour = datetime.now().hour

while True:
    time.sleep(60)
    current_hour = datetime.now().hour
    if current_hour != last_check_hour:
        organize_memory()
        last_check_hour = current_hour
```

### 9.3 Organization Steps

```text
1. Find memories with status "active" that were recently updated.
2. Group by category.
3. Within each category, identify entries with similar keywords or embeddings.
4. Process at most 20 to 50 entries per batch.
5. Ask the LLM to merge, update, or mark entries as outdated.
6. Validate the JSON schema of the output.
7. Write to a temp file.
8. If validation passes, atomically replace the original file.
9. Update index.json.
```

### 9.4 Organization Prompt

```text
Below are related memories from the same category.

Please:
1. Merge duplicate or highly similar entries.
2. If a newer memory replaces an older one, set the older entry's status to "outdated".
3. Do not remove important historical context.
4. Do not add information that was not in the original entries.
5. Keep each summary concise.
6. Output a valid JSON array only. No other text.

[Memory JSON]
...
```

---

## 10. Conflict Resolution Rules

Do not simply keep the newest entry. Use the following rules:

| Situation | Action |
|-----------|--------|
| New information clearly replaces old | Mark old memory as `outdated` |
| New information supplements old | Merge into the same entry |
| Conflict appears context-dependent | Keep both entries |
| User requests deletion | Mark as `deleted` or move to `trash/` |
| User says "don't remember this" | Do not write to memory |

---

## 11. Fault Tolerance and Backup

### 11.1 Dirty Flag

`index.json` uses `needs_organization` to detect abnormal shutdowns:

```text
Organization starts   -> needs_organization = true
Organization succeeds -> needs_organization = false
Program starts        -> if needs_organization is true, re-run organization or restore backup
```

### 11.2 Backup Flow

```text
1. Before organization, copy files to be modified into backup/.
2. Write organization output to a temp file.
3. Validate the temp file.
4. If valid, atomically replace the original file.
5. On success, delete the backup.
6. On failure, restore from backup and retry on the next trigger.
```

### 11.3 Concurrent Write Protection (File Locking)

Background memory extraction and user input can overlap, risking simultaneous writes to the same JSON file. Use file locking to prevent corruption:

```python
import fcntl
import json

def write_memory_safe(filepath, new_entry):
    with open(filepath, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)   # Acquire exclusive lock
        try:
            f.seek(0)
            data = json.load(f)
            data["memories"].append(new_entry)
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)  # Always release lock
```

On Windows, use `msvcrt.locking` or the `filelock` library as a cross-platform alternative:

```python
# Cross-platform option
from filelock import FileLock

lock = FileLock("memory.json.lock")
with lock:
    # safe read/write here
```

All write operations — memory extraction, organization, and manual edits — must go through this locking mechanism.

---

## 12. JSON Validation Rules

Validate every entry before writing:

- Is it valid JSON?
- Does it contain all required fields?
- Is `keywords` an array of 1 to 5 strings?
- Is `summary` a non-empty string?
- Is `category` in the allowed list?
- Is `confidence` a float between 0.0 and 1.0?
- Is `status` one of `active`, `outdated`, `deleted`?
- Are `created_at` and `updated_at` valid ISO 8601 timestamps?

---

## 13. User Control

Provide the following commands or UI:

```text
/memory list          Show everything the AI currently remembers
/memory add           Manually add a memory
/memory edit M.12     Edit a specific memory
/memory delete M.12   Delete a specific memory
/memory off           Pause memory
/memory on            Enable memory
```

Natural language should also be supported:

```text
Remember that I'm building a local AI.
Don't remember what I just said.
What do you remember about me?
Forget the project name I mentioned earlier.
```

---

## 14. Performance Guidelines

For local 4B models, controlling prompt length is the top priority.

| Block | Recommended Token Budget |
|-------|--------------------------|
| System prompt | 300 tokens |
| Relevant memory | 300 to 800 tokens |
| Conversation history | 500 to 1500 tokens |
| Current question | As needed |

Additional recommendations:

- Load only relevant memories per turn.
- Run extraction in the background.
- Keep organization low-frequency and small-batch.
- Use `summary` by default; load `details` only when needed.
- Offer a fast mode (fewer memories, shorter history) and a deep mode (more context).

---

## 15. MVP and Roadmap

### Phase 1 — MVP

1. Implement memory JSON format with all fields.
2. Two-phase background extraction (on user input + after AI response).
3. Keyword-based memory retrieval.
4. Load top 5 memories per prompt turn.
5. File locking for safe concurrent writes.
6. JSON schema validation before every write.
7. Provide `/memory list` and `/memory delete`.

### Phase 2 — Enhancements

1. Embedding-based retrieval.
2. Automatic small-batch organization.
3. Conflict detection and resolution.
4. User memory management UI.
5. Memory usage statistics and capacity display.

---

## 16. Summary

The goal of this memory system is not to store as much data as possible, but to quickly surface a small number of useful memories in each conversation turn.

For a local 4B model, the three most important rules are:

1. Never load all memories into the prompt.
2. Never ask the LLM to organize all memories at once.
3. Let users see and control what the AI remembers.

The three key improvements over the original design are:

- **Two-phase extraction** — captures user-stated facts immediately, not just after the AI responds.
- **Confidence scoring rules** — defines who assigns scores and what thresholds mean, so low-quality memories are filtered out automatically.
- **File locking** — prevents data corruption when background extraction and user input overlap.

Once Phase 1 is complete, the system will deliver noticeable personalization without significantly slowing down response times.
