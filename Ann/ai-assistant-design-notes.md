# Ann AI Assistant — Initial Design Notes

> Discussion date: 2026-05-26

---

## 1. Language Selection

### Recommended: Python

For an AI assistant with a self-updating mechanism, Python is the best choice:

- The richest AI/LLM ecosystem (LangChain, Anthropic SDK, OpenAI SDK, etc.)
- Very convenient dynamic module loading (`importlib`), ideal for hot-updates
- Simple subprocess / git operations
- Mature testing framework (pytest)
- Cross-platform with flexible deployment

### Comparison with Other Options

| Language | Pros | Cons |
|----------|------|------|
| **Node.js** | Strong async, good frontend integration | AI ecosystem less mature than Python |
| **Go** | Fast compilation, simple deployment | Complex dynamic module loading |
| **Rust** | Excellent performance | Slow development cycle, weak AI ecosystem |

---

## 2. Self-Updating Mechanism Design (Local Environment)

### Core Challenge

A Python program cannot directly replace its own running files. The solution is a **Launcher + Core separation** architecture:

```
launcher.py   ← Never updated; only responsible for starting and monitoring
    └── assistant.py  ← This part can be updated and restarted
```

### Update Flow

```
1. assistant detects a new version
2. Notifies launcher: "ready to update"
3. launcher downloads and tests the new version
4. launcher kills the old assistant
5. launcher restarts with the new version
6. On failure: rollback to the previous version
```

### Local-Specific Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| Cannot overwrite running files | Launcher + Core architecture separation |
| Dependency updates (pip) | virtualenv isolation; test new version in a fresh venv |
| User is mid-conversation | Schedule update during conversation gaps, or ask the user |
| No network / GitHub unreachable | Graceful fallback; continue with the current version |
| Test env differs from runtime env | Run tests in isolation via subprocess on the same machine |

---

## 3. Recommended Directory Structure

```
~/.ai-assistant/
├── launcher.py          # Core launcher — rarely updated
├── current/             # Currently running version
│   ├── assistant.py
│   ├── plugins/
│   └── requirements.txt
├── staging/             # Download new version here for testing first
├── versions/            # Keep old versions (for rollback)
│   ├── v1.0.2/
│   └── v1.0.1/
├── config.yml           # User settings — never overwritten by updates
└── logs/
```

---

## 4. GitHub API Update Mechanism

### Available APIs

**Compare versions:**
```
GET https://api.github.com/repos/{owner}/{repo}/releases/latest
```
Returns `tag_name`; compare with the local `version.txt` to determine if an update is needed.

**Download source code:**
```
GET https://api.github.com/repos/{owner}/{repo}/zipball/{tag}
```
Use `requests` or the built-in `urllib` to download the zip and extract it to `staging/`.

**Verify integrity:**
```
GET https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{tag}
```
Compare the commit SHA to confirm the download is correct.

### Complete Update Flow (Pure API — No git Commands Required)

```
1. GET /releases/latest       → Fetch the latest tag
2. Compare with local version.txt → Is an update needed?
3. GET /zipball/{tag}         → Download the zip
4. Verify SHA                 → Confirm integrity
5. Extract to staging/        → Prepare for testing
6. Run pytest (subprocess)    → Only swap if tests pass
7. Atomic swap → current/     → Restart assistant
8. Failure → clear staging    → Notify the user
```

### Token Requirements

| Scenario | Token Required? |
|----------|----------------|
| Public repo, read-only | ❌ Not required |
| Private repo | ✅ Requires a Personal Access Token |
| Avoid rate limit (60/hour) | ✅ Recommended; raises limit to 5,000/hour |

---

## 5. User Experience Design

The local assistant can interact directly with the user to confirm updates:

```
Ann: "New version v1.2.0 is available. It includes:
      - Added memory feature
      - Improved response speed
      Update now? (yes / later / skip this version)"
```

---

## 6. Version Management Strategy

- Use **git tags** to mark stable versions; only update from tags, not directly from the main branch
- Keep the last N versions for rollback
- Verify GitHub commit signatures (to prevent malicious injection)
- Run tests in an isolated environment (subprocess / virtualenv)

---

## 7. Recommended Implementation Order

1. **Launcher** — simplest, but most critical
2. **GitHub version detection** — compare tags via GitHub API
3. **Test + swap mechanism** — ensure safe updates
4. **AI conversation core** — add last

Each step can be validated independently, avoiding excessive complexity from the start.
