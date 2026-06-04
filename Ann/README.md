# Ann: AI Assistant with Self-Updating Mechanism

Welcome to the **Ann** AI assistant project. Ann is a locally-hosted Python AI assistant featuring an automatic self-updating mechanism.

---

## 📌 Project Overview

This project adopts a **Launcher + Core (separated processes)** architecture to overcome the limitation that a Python process cannot overwrite its own running files. Version management and file delivery are handled entirely through the GitHub REST API, enabling painless updates and rollbacks.

---

## 🛠️ Development Language & Tech Stack

- **Core Language**: Python 3.10+
  - **Advantages**: The richest AI/LLM ecosystem (LangChain, Anthropic SDK, OpenAI SDK), easy dynamic module loading (`importlib`), simple subprocess and OS operations.
- **Test Framework**: `pytest`
- **Dependency Management**: `pip` + `virtualenv` / `venv`
- **Communication Protocol**: GitHub REST API (HTTPS)

### Language Comparison

| Language | Pros | Cons | Suitability |
| :--- | :--- | :--- | :---: |
| **Python** | Complete LLM ecosystem, hot-update friendly, rapid development | Slower execution speed | ⭐⭐⭐⭐⭐ (Recommended) |
| **Node.js** | Strong async performance, easy front-end integration | AI ecosystem less mature than Python | ⭐⭐⭐ |
| **Go** | Fast compilation, simple single-binary deployment | Complex dynamic module loading/updating logic | ⭐⭐ |
| **Rust** | Excellent performance and safety | Longer development cycle, weak AI ecosystem | ⭐ |

---

## 🏗️ Core Architecture: Launcher + Core Dual-Module

To solve the "cannot overwrite running code" local limitation, the project splits program logic into two components:

- **`launcher.py`** (Launcher): Always running, rarely updated. Responsible for starting and monitoring the `assistant.py` core, and executing test-and-swap for new versions.
- **`assistant.py`** (Ann Assistant Core): Thin CLI entry point. Handles startup, system commands (exit/restart/update), and delegates conversation to `CoreController`.
- **`core_controller.py`** (CoreController): Unified business logic layer shared by CLI and GUI. Runs the full conversation pipeline: moral evaluation → memory → intent routing → Ollama fallback.
- **`intent_router.py`** (IntentRouter): Plugin registry. Registers `BaseIntentParser` modules (alarm, file, news, …) and routes each user message to the first matching module via `should_parse() → parse_intent() → execute()`.
- **`assistant_gui.py`** (Ann GUI): Thin PyQt6 presentation layer. Uses `ControllerWorker(QThread)` to run `CoreController.post_message()` in the background, keeping the UI fully responsive.


```mermaid
graph TD
    Launcher["launcher.py\nPersistent monitor — never auto-updated"]
    Updater["updater.py\nUpdate orchestrator — never auto-updated"]
    Assistant["current/assistant.py\nAnn AI assistant core & user interaction"]
    Staging["staging/\nNew version download & pytest validation"]
    Versions["versions/\nHistorical backups for rollback"]
    GitHub["GitHub API\nCommit & file delivery"]

    Launcher -->|Start & restart monitoring| Assistant
    Assistant -->|Update confirmed, exit 42| Launcher
    Assistant -->|Restart requested, exit 3| Launcher
    Launcher -->|Delegate update| Updater
    Updater -->|1. Fetch latest commit| GitHub
    Updater -->|2. Download files| Staging
    Updater -->|3. Run pytest| Staging
    Updater -->|4. Backup current| Versions
    Updater -->|5. Atomic swap| Assistant
    Updater -->|6. Post-swap self-test| Assistant
    Updater -.->|Self-test fails: rollback| Versions
    Launcher -.->|Startup crash after update: rollback| Versions
```

## 🧩 Adding a New Module — Rules & Guidelines

Ann 採用 **IntentRouter + BaseIntentParser** 的插件架構。每個功能模組是一個獨立的類別，只要遵守以下規範，就能在不修改任何現有業務邏輯的情況下掛載新功能。

---

### 1. 插件合約（Plugin Contract）

所有功能模組**必須**繼承 `BaseIntentParser`，並實作以下 5 個方法：

```python
from base_intent_parser import BaseIntentParser, ModuleResult

class MyModule(BaseIntentParser):
    # ── 必填：關鍵字清單（快速前置過濾，不呼叫 Ollama）──────────────────
    KEYWORDS = ["my_keyword", "我的功能"]

    # ── 必填：給 Ollama 的系統提示（定義 JSON schema）────────────────────
    def _build_system_prompt(self) -> str:
        return "Your system prompt here..."

    # ── 必填：驗證 Ollama 回傳的 JSON，確保欄位型別正確 ─────────────────
    def _validate_and_normalize(self, result: dict) -> dict:
        # 確保 intent 只有允許的值
        if result.get("intent") not in {"do_something", "none"}:
            result["intent"] = "none"
        return result

    # ── 必填：當 intent 沒有命中時回傳的空結果 ───────────────────────────
    def _empty_result(self) -> dict:
        return {"intent": "none", "param": None}

    # ── 必填：Ollama 離線或 JSON 解析失敗時的 regex 備援邏輯 ─────────────
    def _regex_fallback(self, text: str) -> dict:
        if "my_keyword" in text.lower():
            return {"intent": "do_something", "param": text}
        return self._empty_result()

    # ── 必填：模組的業務邏輯，回傳 ModuleResult ───────────────────────────
    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        reply = f"Handled: {parsed.get('param', '')}"
        return ModuleResult(reply=reply)
```

> [!IMPORTANT]
> `execute()` 會在 **背景執行緒（ControllerWorker）** 中被呼叫。可以自由執行阻塞式 I/O（網路請求、檔案讀寫、Ollama 呼叫），**不可**在 `execute()` 中直接操作任何 Qt 物件（Widget、QLabel、QTimer 等）。

---

### 2. `context` 字典 API

`execute()` 的第二個參數 `context` 由 `CoreController.post_message()` 提供，包含以下保證可用的鍵：

| Key | 型別 | 說明 |
|:----|:-----|:-----|
| `config` | `dict` | 完整的 `config.yml` 設定 |
| `conversation` | `list[dict]` | 當前對話歷史（`[{"role": "user"/"assistant", "content": "..."}]`）|
| `base_dir` | `Path` | Ann 根目錄（用於讀寫持久化資料）|
| `user_text` | `str` | 使用者原始輸入文字 |
| `call_llm` | `Callable[[str], str]` | 直接呼叫 Ollama 的同步函式，接受單一 prompt 字串 |
| `alarm_manager` | `AlarmManager \| None` | 鬧鐘管理員實例 |
| `news_manager` | `NewsManager \| None` | 新聞管理員實例 |

> [!NOTE]
> 如果您的模組需要自己初始化的物件（如資料庫連線、API client），請在模組的 `__init__` 中初始化並儲存為 `self.xxx`，**不要**透過 `context` 傳入（context 只提供全域共享資源）。

---

### 3. 使用 `conversation` 的注意事項

- `conversation` 是 **共享的可變 list，所有模組共用同一份對話歷史。
- 在 `execute()` 中**不要直接 append** 到 `conversation`——`CoreController` 會在路由成功後自動處理對話記錄。
- 若您的模組需要呼叫 `call_llm()` 並希望對話記錄包含此次交流，**請在 `execute()` 回傳後**，透過 `CoreController` 的標準流程處理（而非在 execute 內手動 append）。

---

### 4. `ModuleResult` 欄位說明

```python
@dataclass
class ModuleResult:
    reply: str                  # 必填：要顯示給使用者的文字
    articles: list = []         # 選填：新聞卡片清單（僅新聞模組使用）
    marker: str | None = None   # 選填：控制指令，如 '[EXIT]', '[RESTART]'
```

> [!WARNING]
> `marker` 欄位僅保留給系統層級的控制流程（退出、重啟、更新）。**一般功能模組不應設定 `marker`。**

---

### 5. 命名與檔案位置規範

| 規範項目 | 要求 |
|:---------|:-----|
| **模組目錄** | 若功能複雜，建立 `current/<your_module>/` 子目錄；單一功能可直接放 `current/<your_module>_handler.py` |
| **IntentParser 類別名稱** | 以 `IntentParser` 結尾，例如 `TodoIntentParser` |
| **KEYWORDS** | 使用中英文混合，盡量涵蓋使用者可能的輸入方式 |
| **`_build_system_prompt()`** | 必須明確要求 Ollama 只回傳 JSON，並附上欄位 schema |
| **測試檔案** | 必須在 `current/tests/test_<your_module>.py` 建立對應單元測試 |

---

### 6. 註冊模組

模組建立後，在 `CoreController.setup_modules()` 中註冊：

```python
# current/core_controller.py → CoreController.setup_modules()
def setup_modules(self) -> None:
    # ... 現有模組 ...

    from my_module import MyModule  # 替換為您的模組
    my_module = MyModule(self.llm_base_url, self.llm_model)
    self.router.register(my_module)
```

> [!IMPORTANT]
> **路由器是有序的（first-match-wins）**。在 `register()` 的呼叫順序決定了優先級：排在前面的模組會先被嘗試。請將**特定性更高**的模組放在前面，**通用型**的模組放在後面，避免過度攔截。

---

### 7. 禁止事項

| ❌ 禁止 | ✅ 應改為 |
|:--------|:---------|
| 在 `execute()` 內操作 Qt Widget | 透過 `ModuleResult.reply` 回傳文字，由 GUI 渲染 |
| 在模組內直接存取 `assistant_gui.py` | 透過 `context` 取得所需資料 |
| 在 `execute()` 內 `append` 到 `context["conversation"]` | 讓 `CoreController` 在路由後自動記錄 |
| 在模組內實作 exit / restart / update 等系統指令 | 系統指令只在 `assistant.py` / `assistant_gui.py` 的主迴圈中處理 |
| 在 `should_parse()` 中呼叫 Ollama | `should_parse()` 必須是純關鍵字比對，不允許任何 I/O |

---

### 8. 快速範例：新增一個 TodoModule

**Step 1 — 建立 `current/todo_handler.py`**

```python
from base_intent_parser import BaseIntentParser, ModuleResult

class TodoIntentParser(BaseIntentParser):
    KEYWORDS = ["todo", "待辦", "任務清單", "提醒我"]

    def _build_system_prompt(self) -> str:
        return (
            "Extract todo intent from the user message.\n"
            "Respond ONLY with valid JSON: "
            '{"intent": "add_todo | list_todo | none", "content": "string or null"}'
        )

    def _validate_and_normalize(self, result: dict) -> dict:
        if result.get("intent") not in {"add_todo", "list_todo", "none"}:
            result["intent"] = "none"
        return result

    def _empty_result(self) -> dict:
        return {"intent": "none", "content": None}

    def _regex_fallback(self, text: str) -> dict:
        if "todo" in text.lower() or "待辦" in text:
            return {"intent": "add_todo", "content": text}
        return self._empty_result()

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        base_dir = context["base_dir"]
        todo_file = base_dir / "todos.txt"

        if parsed["intent"] == "add_todo":
            content = parsed.get("content") or context["user_text"]
            with open(todo_file, "a", encoding="utf-8") as f:
                f.write(f"- {content}\n")
            return ModuleResult(reply=f"✅ 已新增待辦：{content}")

        if parsed["intent"] == "list_todo":
            if todo_file.exists():
                items = todo_file.read_text(encoding="utf-8").strip()
                return ModuleResult(reply=f"📋 待辦事項：\n{items}" if items else "目前沒有待辦事項。")
            return ModuleResult(reply="目前沒有待辦事項。")

        return ModuleResult(reply="")
```

**Step 2 — 在 `CoreController.setup_modules()` 中註冊**

```python
from todo_handler import TodoIntentParser
todo_parser = TodoIntentParser(self.llm_base_url, self.llm_model)
self.router.register(todo_parser)
```

**Step 3 — 在 `tests/test_todo.py` 補上單元測試，完成。**

---

## ⚙️ Installation & Usage (安裝與使用)

### 1. Prerequisites (環境要求)
- **Python**: Version 3.10 or higher.
- **Ollama**: Local LLM server running on your machine.
  - Install Ollama from [ollama.com](https://ollama.com).
  - Pull and run the default model specified in [config.yml](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/config.yml) (typically `gemma4:e4b`):
    ```bash
    ollama run gemma4:e4b
    ```

### 2. Dependency Installation (安裝依賴)
Install the required packages from the dependency manifest:
```bash
pip install -r current/requirements.txt
```
This installs `PyQt6` (for GUI), `pygame` (for audio alarms), `ollama` (for API integration), `requests` (for HTTP APIs), `pyyaml` (for configuration parsing), `pytest` (for unit testing), and all news module dependencies (`feedparser`, `newspaper3k`, `readability-lxml`, `beautifulsoup4`, and `httpx`).

### 3. Running Ann (啟動方式)
You can run Ann in two modes. The launcher automatically monitors and updates the core:
- **GUI Mode (Default)**:
  ```bash
  python launcher.py
  ```
  Launches a floating bubble avatar. Click to expand into a full dark-mode chat window, drag to reposition, and click the dismiss button or the bubble itself to shut off active alarms.

- **CLI Mode (Terminal)**:
  ```bash
  python launcher.py --cli
  ```
  Runs as a conversational shell in the terminal. If an alarm triggers, it prints reminder alerts every 2 seconds and can be dismissed by pressing Enter.

### ⏰ Alarm Module (鬧鐘功能)
Ann supports conversational alarm management (create, delete, list) through natural conversation. You can set relative/absolute alarms, check active alarms, and cancel them.
For complete architectural details, audio loop specs, and UI animations, see [alarm_module_spec.md](./alarm_module_spec.md).

### 📂 Drag & Drop Module (拖放功能)
Ann supports dragging and dropping plain text and image files onto the floating bubble or the chat window. Dropped files are attached to the conversation context and can be clicked to display a popup preview (viewing full text or images).
For detailed interaction specifications, see [drag_drop_spec.md](./drag_drop_spec.md).

### 🤖 AI Engine Module (AI 引擎模組)
Ann encapsulates all communication with the local Ollama API into a modular `OllamaClient` component within the AI Engine. It automatically detects installed models and their capabilities (such as vision support). When an image is attached, it dynamically routes the request to a local vision-capable model (like `llava`) or guides the user if none is installed.
For technical details, see [ai_engine_spec.md](./ai_engine_spec.md).

### 📝 File Generation & Export Module (檔案生成與匯出功能)
Ann supports exporting and saving AI-generated code blocks and documentation directly to the local filesystem:
- **UI-Based Saving**: Code blocks in the chat GUI are rendered with a custom code container displaying a language badge and a "Save File" button, allowing quick, secure, and filtered saving for `.py`, `.c`, `.cpp`, `.java`, `.sh`, `.html`, `.xml`, `.css`, `.js`, `.ts`, `.sql`, `.toml`, `.env`, `.md`, and `.txt` files.
- **Conversational Saving (Option C)**: You can request file generation directly in the dialogue (e.g., "把剛才的 code 儲存為 app.py" or "匯出對話紀錄到 history.md"). Ann will parse the intent locally and save the file directly to the workspace directory.

For complete specs, see [file_generation_spec.md](./file_generation_spec.md).

### 📰 News Module (新聞模組)
Ann supports conversational news queries using local Ollama model to parse search intents, retrieve and parse RSS feeds (e.g. Google News, Reuters), filter articles by keywords/categories, and generate concise article summarizations (3–5 sentences) in Traditional Chinese upon request.
For full specifications, caching policies, and architecture, see [news_module_spec.md](./news_module_spec.md).

### 🧠 Memory Module (記憶模組)
Ann integrates a local conversational memory system designed in [AI_Memory_System_Design_v2.md](./AI_Memory_System_Design_v2.md) to persist user context across CLI and GUI sessions:
- **Two-Phase Background Extraction**: Facts stated by the user are extracted on input (Phase 1), and commitments/conclusions are extracted after response generation (Phase 2) using separate background threads.
- **Concurrent Safe Persistence**: Stored under `memory/` directory via daily JSON file slices and managed registry index with strict `filelock` synchronization.
- **On-Demand Context Injection**: Prompts are dynamically augmented by retrieving and ranking the top 5 most relevant active memories based on keyword overlap and date recency weights.
- **Commands Control**: Full user override control using `/memory` slash commands:
  - `/memory list` — Lists all currently remembered active context.
  - `/memory add <content>` — Manually registers a new context fact.
  - `/memory edit <id> <new_content>` — Modifies a specific memory by its ID.
  - `/memory delete <id>` — Discards a specific context memory.
  - `/memory off` / `/memory on` — Globally pauses/resumes the memory layer.

### 🛡️ Security Mode (安全監控模式)
Ann supports a conversational security monitoring mode backed by the `realtime-security-daemon` design:
- **Conversation-Triggered Switch**: Say "開啟安全模式" / "enable security mode" to enter, or "關閉安全模式" / "exit security mode" to leave. The switch is handled by `SecurityIntentParser` — no additional GUI controls needed.
- **Bubble Visual Feedback**: The floating bubble switches to a dual-ring red pulse effect (outer faint halo + inner breathing ring) while security mode is active. The inner circle colour is unchanged.
- **Security Dashboard**: The chat content area switches to a compact dashboard showing Daemon status, Queue depth, and a scrollable alert feed with severity colour coding and click-to-expand details including MITRE ATT&CK mapping and response recommendations.
- **Persistent Input Bar**: The conversation input bar remains available in security mode so you can continue asking questions.
- **Update Lock**: For system safety and operational integrity, program updates cannot be checked or performed while security monitoring mode is active ("在安全模式下，是無法進行更新的").
- **Status Queries**: Ask "有幾個告警" / "daemon 狀態" for a plain-text status summary without entering full dashboard mode.
- Phase 1 uses mock data; Phase 2 will read from the real security daemon's `alerts.jsonl` / SQLite store.
For the daemon architecture and UI spec, see the [`realtime-security-daemon/`](./realtime-security-daemon/) directory.

### 🔄 Conversational System Commands (對話式系統指令)
Ann supports executing system actions directly through natural conversation, featuring warm LLM response generation prior to execution:
- **Exit Program (關閉程式)**: Commands like "再見", "關閉視窗", "exit", "close the app" trigger a warm goodbye, append `[EXIT]`, disable inputs, and shut down after a 1.5 seconds delay.
- **Restart Program (重啟程式)**: Commands like "重啟", "重新啟動", "restart", "reboot" trigger a warm "see you later" reply, append `[RESTART]`, and relaunch the assistant immediately.
- **Update Program (系統更新)**: Commands like "更新", "升級", "update" trigger an update check. Upon confirmation, Ann replies with a warm goodbye, appends `[UPDATE]`, and runs the self-updater.

---

## 📂 Recommended Directory Structure

The recommended layout for deployment and development:

```text
~/.ai-assistant/
├── launcher.py              # Core launcher (rarely updated, never overwritten)
├── updater.py               # Update orchestrator (rarely updated, never overwritten)
├── moral_module_spec.md     # ⚖️ Moral & safety specification (DO NOT MODIFY)
├── config.yml               # User configuration (preserved across updates)
├── config/                  # Configuration directory
│   └── news_sources.yml     # RSS news sources definitions
├── version.txt              # Current version string (managed by updater)
├── logs/                    # System logs
├── memory/                  # AI memory persistence directory (preserved across updates)
│   ├── index.json           # Memory registry index tracking metadata
│   └── memories/            # Date-sliced daily memory files YYYY-MM-DD_memory.json
├── current/                 # Active production version (auto-updated)
│   ├── assistant.py         # Ann AI assistant — CLI entry point
│   ├── assistant_gui.py     # Ann AI assistant — GUI (PyQt6/PySide6)
│   ├── alarm_handler.py     # Shared alarm intent dispatch (CLI + GUI)
│   ├── memory_manager.py    # AI Memory System core logic and thread manager
│   ├── ollama_client.py     # Unified Ollama API client with vision routing
│   ├── file_handler.py      # File generation & export intent handler
│   ├── moral_evaluator.py   # Moral/safety risk classifier
│   ├── security_plugin.py   # Security mode intent parser plugin
│   ├── security_dashboard.py# Security Dashboard widget (QStackedWidget view)
│   ├── version_check.py     # GitHub API version check helper
│   ├── alarms/              # Alarm storage and scheduler
│   ├── news/                # News parsing, fetching, extracting, and summarization
│   ├── plugins/             # Plugin extension directory
│   ├── requirements.txt     # Dependencies for this version
│   └── tests/               # Unit tests (run in staging before each update)
│       └── test_memory.py   # AI Memory System unit tests
├── staging/                 # Update buffer (download, test, then swap here)
└── versions/                # Historical version backups (for rollback)
    ├── v20260101-abc1234/
    └── v20260201-def5678/
```

---

## 🔄 Self-Updating Flow

This system requires **no local git commands** — it relies entirely on the **GitHub REST API** for version control and file delivery.

> [!IMPORTANT]
> **Strict Design Rule**: The update mechanism MUST use the GitHub REST API (HTTP) for all version checking, file listings, and downloads. Using local `git` commands (such as `git pull` or `git fetch`) within the update flow is strictly prohibited to ensure Ann can self-update even when deployed in non-Git target environments.


### 1. Update Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant A as current/assistant.py
    participant L as launcher.py
    participant S as staging/
    participant GH as GitHub API

    A->>GH: 1. Check latest commit (GET /commits/{branch})
    GH-->>A: Return latest commit (date & SHA)
    Note over A: Format YYYYMMDD-sha and compare with local version.txt

    rect rgb(230, 245, 255)
        Note over A, U: If a new version is available
        A->>U: 2. "New version detected. Update now?"
        U-->>A: Confirm update (Yes)
    end

    A->>L: 3. Send update signal and exit
    L->>GH: 4. Fetch Ann file list (GET /contents/Ann?ref={branch})
    GH-->>L: Return JSON file list (each entry includes download_url)
    L->>GH: 5. Download Ann files (iterate download_url for each file)
    L->>S: 6. Write files to staging/ at their relative paths

    rect rgb(240, 255, 240)
        Note over L, S: Safety validation phase
        L->>S: 7. Run pytest and dependency check in staging
        S-->>L: All tests pass
    end

    L->>L: 8. Atomic swap: staging/ -> current/
    L->>A: 9. Restart new version of assistant.py (Ann)
```

### 2. GitHub API Details

* **Check latest branch commit:**
  ```http
  GET https://api.github.com/repos/{owner}/{repo}/commits/{branch}
  ```
  Extract `commit.committer.date` (formatted as `YYYYMMDD`) and `sha` (first 7 characters) and combine them into `YYYYMMDD-sha`. Compare this formatted string with the local `version.txt` to determine whether an update is needed.

* **Fetch file list for the Ann directory:**
  ```http
  GET https://api.github.com/repos/zohanlin2-ai/AI-coding-only/contents/Ann?ref={branch}
  ```
  Returns a JSON list of files and subdirectories under `Ann/`.

* **Download a single file (raw content):**
  ```http
  GET https://raw.githubusercontent.com/zohanlin2-ai/AI-coding-only/{branch}/Ann/{path_to_file}
  ```
  Each file's `download_url` from the JSON list is used to download the file directly into the corresponding path under `staging/`. This approach downloads **only the `Ann` project** — not the entire repository.

> [!TIP]
> **API Access & Rate Limits:**
> - **Public Repo**: No token required, but limited to 60 requests/hour.
> - **Private Repo**: Must include a Personal Access Token (PAT) in the header — `Authorization: Bearer <YOUR_TOKEN>`.
> - **Recommendation**: Even for public repos, configuring a token raises the limit to 5,000 requests/hour.


---

## ⚠️ Local Environment Challenges & Solutions

| Challenge | Solution |
| :--- | :--- |
| **File lock / in-use** | Python cannot modify its own running code. `launcher.py` spawns `assistant.py` as a subprocess; during update, the child process is terminated, files are swapped, and it is restarted. |
| **Dependency updates (`pip`)** | New versions may introduce new third-party packages. `virtualenv` isolation in `staging/` validates new dependencies before writing to the production environment. |
| **Interrupting active conversation** | The update prompt is shown at conversation breaks. The user may choose "later" or "skip this version" to avoid unwanted interruptions. |
| **Network unavailable** | GitHub API calls fail when offline. A graceful fallback keeps the existing version running and records the failure in the log. |

### 💬 UX Interaction Example

When a new version is detected, the assistant proactively prompts the user rather than forcing an update:

```text
Ann: "New version v1.2.0 is available. It includes:
      - Added memory feature
      - Improved response speed
      Update now? (yes / later / skip this version)"
```

---

## ⚖️ Moral & Safety Specification Module

This project integrates [moral_module_spec.md](./moral_module_spec.md) to evaluate user requests, system actions, and autonomous decisions, ensuring Ann's behavior aligns with ethical principles, safety constraints, and accountability requirements.

> [!IMPORTANT]
> **Moral Module Authorship & Audit Declaration:**
> - **Designed by**: **OpenAI**
> - **Audited by**: **Claude**
> - **⚠️ Modification strictly prohibited**: **No one is permitted to modify `moral_module_spec.md`.** The integrity of Ann's moral baseline depends on this file remaining unchanged.

### 🛑 Protected Updates in the Self-Updating Mechanism

Per [moral_module_spec.md](./moral_module_spec.md) §20, the moral module is a **protected component**:

1. **No automatic updates**: Any change to the moral module, its prompts, policies, classifiers, tool permissions, or risk thresholds **must never** be applied silently via the auto-update mechanism (`allowAutomaticMoralUpdates: false`).
2. **Explicit confirmation required**: Updates to the moral module require explicit approval from the user or an authorized operator, must pass a safety and regression test suite, and must provide a rollback path to the previous version.

### ⚠️ Current Implementation Status & Limitations

- **Rule-Based Engine**: The moral evaluator currently uses a deterministic regex rules engine for risk classification. It does not yet employ a hybrid/semantic LLM classifier.
- **Risk of Over-Refusal (False Positives)**: Due to the keyword/regex nature, benign or fictional requests containing sensitive terms (e.g., educational or creative writing requests) may trigger unnecessary refusals or safeguards.
- **Simplified Interface**: The current implementation handles basic risk assessment and output decisions but does not yet support the full Section 26 data structure, audit log generation, or E1–E5 local escalation confirmation dialogs.

---

## 🤖 AI Coding Guidelines (CLAUDE.md)

> [!IMPORTANT]
> All contributors — including AI coding assistants — **must read and follow [CLAUDE.md](./CLAUDE.md) before making any code changes.**
>
> Key principles:
> - **Think before coding**: state assumptions, surface tradeoffs, ask when uncertain.
> - **Simplicity first**: minimum code that solves the problem; no speculative features.
> - **Surgical changes**: touch only what is necessary; match existing style.
> - **Goal-driven**: define verifiable success criteria before starting.

---

## 🚀 Development Roadmap

To minimize complexity, implement the project in the following order:

1. **Step 1: Persistent Launcher**
   - Implement `launcher.py` to spawn `assistant.py` as a subprocess and monitor its lifecycle.
2. **Step 2: GitHub Version Detection**
   - Implement the API call, compare tag versions, and signal the launcher when an update is available.
3. **Step 3: Secure Download & pytest Validation**
   - Fetch the `Ann/` file list via the Contents API, download each file into `staging/`, then run `pytest` in an isolated environment using `subprocess`.
4. **Step 4: Atomic Swap & Rollback**
   - Implement directory swap logic; on test failure, clear `staging/`, retain the current version, and notify the user.
5. **Step 5: AI Dialogue, Plugin System & Moral Module Integration**
   - Integrate an LLM SDK (e.g. Ollama, LangChain, or Anthropic/OpenAI SDK) into `assistant.py`, and wire up the decision pipeline and risk classifier defined in [moral_module_spec.md](./moral_module_spec.md) to complete Ann's full core functionality.
