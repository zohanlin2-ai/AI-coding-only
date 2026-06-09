# Changelog

All notable changes to the **Ann** AI assistant project will be documented in this file.

## [0.2.6] - 2026-06-09

### Added
- **Graceful model resolution at startup** (`current/ollama_client.py` → `OllamaClient.resolve_model()`): determines the effective chat model with graceful degradation — (1) use the model from `config.yml` if it is installed, (2) otherwise fall back to the first model Ollama lists as available, (3) if no model is available at all (Ollama not running or no models pulled), return `None`. `CoreController.__init__()` calls this once, stores the result on `self.llm_model`, exposes a `self.llm_available` flag, and writes the resolved name back into the shared config dict so secondary consumers (SecurityDaemon, network monitor) use the same model.
- **LLM-free degradation notice**: when no LLM is available, Ann still launches so the LLM-free slash commands (`/help`, `/version`, `/model`, `/models`, `/switch`, `/memory`, …) remain usable. The CLI prints a startup banner warning; the GUI shows a persistent `⚠️ No LLM` badge in the title bar plus an initial chat notice directing the user to `/help`.
- Unit tests for `resolve_model()` covering preferred-available, fallback-to-first, and none-available cases (`current/tests/test_model_routing.py`).

## [0.2.5] - 2026-06-09

### Added
- **Memory Phase 2 — Usage Statistics** (`/memory stats`): new `get_stats()` method on `MemoryManager` reads active, outdated, deleted, and total counts plus file count and storage size from the index. Exposed via `/memory stats` in `handle_memory_command()` for both CLI and GUI.
- **Memory Phase 2 — Semantic Embedding Retrieval**: `retrieve_memories()` now attempts to obtain an Ollama embedding vector (`/api/embeddings`) for the user query and each candidate memory summary, computing cosine similarity (no numpy dependency). When embeddings are available, scoring blends cosine similarity (0.50) + keyword overlap (0.25) + recency/confidence (0.25), and all active memories are evaluated regardless of keyword overlap. Falls back silently to the original keyword-only formula when the endpoint is unavailable.
- **Memory Phase 2 — Conflict Detection**: after every `add_memory()` call, a background thread calls the LLM to check whether the new summary directly contradicts any existing active memory in the same category with overlapping keywords. Conflicting entries are automatically marked `outdated` so they no longer appear in retrieval. Skips quietly on any LLM or network failure.
- **Memory Phase 2 — Auto Organization**: every 20 active memories, `add_memory()` sets `needs_organization=True` in the index and launches a background organization pass. The pass clusters same-category memories sharing ≥2 keywords (confidence ≥0.7, group of ≥3), asks the LLM to merge each cluster into one concise summary, and replaces the originals with a single consolidated entry. `last_organized` timestamp is recorded in the index after each pass.
- **Memory Phase 2 — Memory Management UI** (`/memory ui`): new `memory_dialog.py` provides a dark-mode `MemoryDialog` (QDialog) with a scrollable list of active memories, category filter dropdown, per-row inline edit (pencil → save), and delete with confirmation. In GUI mode, `/memory ui` opens the dialog immediately (no LLM call). In CLI mode, `/memory ui` returns a message directing the user to GUI mode.

### Changed
- `core_controller.py` — `handle_memory_command()` help string updated: `stats` and `ui` added to command list.
- `assistant_gui.py` — `send_message()`: `/memory ui` branch added before the generic `handle_memory_command()` delegation.

## [0.2.4] - 2026-06-09

### Added
- **Model Management Plugin** (`current/model_handler.py`): new `ModelIntentParser` plugin for LLM-backed model query and switching. Classifies intents as `query_current` / `query_available` / `switch_model` / `none` via Ollama, with a broad keyword pre-filter and a regex fallback for switch detection. Switching updates all registered parser instances in-session and persists the new model name to `config.yml`.

### Changed
- `core_controller.py` — `setup_modules()`: registers `ModelIntentParser` after `SecurityIntentParser`.
- `core_controller.py` — `post_message()`: added `"controller"` key to the context dict so plugins can access the `CoreController` instance directly.

## [0.2.3] - 2026-06-05

### Added
- **Network Connection Status Monitoring (NetworkCollector)** (`current/security_daemon.py`): New zero-dependency network collector checking TCP connection states using PowerShell json outputs on Windows and netstat fallbacks on Linux/macOS. Adds active detection of Command and Control (C2) servers via rule `R-003`.
- **Unit Tests for Network Mode** (`current/tests/test_security_daemon.py`): Appended unit tests `test_network_collector_parsing` and `test_r003_rule_matching` to verify Windows/Unix output parsing and matching logic.

### Changed
- **Security Dashboard Coverage Integration** (`current/security_dashboard.py`): Updated CSF coverage table and MITRE ATT&CK coverage table mapping to show `R-003` active and mapped to MITRE C2 tactic.

## [0.2.2] - 2026-06-04

### Added
- **Security Mode Plugin** (`current/security_plugin.py`): new `SecurityIntentParser` plugin that detects security mode switch requests and status queries. Follows the standard `BaseIntentParser` plugin contract. Returns `[SECURITY_ON]` / `[SECURITY_OFF]` embedded in the reply text, flowing through the existing `parse_reply_marker()` pipeline.
- **Security Dashboard** (`current/security_dashboard.py`): new `SecurityDashboardWidget` displayed inside `ChatWindow` when security mode is active. Shows compact status cards (Daemon / Queue / Alerts) and a scrollable alert feed with click-to-expand detail rows and response recommendations. Uses mock data in Phase 1; real daemon reads in Phase 2.
- Extended `_MARKERS` in `alarm_handler.py` to include `[SECURITY_ON]` and `[SECURITY_OFF]`, reusing the same marker-stripping pipeline as `[EXIT]` / `[RESTART]`.

### Changed
- `assistant_gui.py` — `ChatWindow`: added `QStackedWidget` that holds the chat scroll area (index 0) and `SecurityDashboardWidget` (index 1); added `enter_security_mode()` / `exit_security_mode()` helpers; added `🛡️ Security` badge in title bar; `handle_controller_result()` now handles `[SECURITY_ON]` / `[SECURITY_OFF]` markers; `input_field` placeholder changes per mode. Blocked update checks and update confirmations when security mode is active, and added pre-update checks to stop the SecurityDaemon if it is currently running. Pauses the SecurityDaemon collectors during ControllerWorker background message generation and resumes them when finished.
- `assistant.py` (CLI mode): added state tracking for security mode via markers, blocking update commands and update confirmations if security mode is active. Also checks and stops the SecurityDaemon before proceeding with updates. Pauses collectors during blocking Ollama message generation and resumes them afterwards.
- `security_daemon.py`: implemented `pause()` / `resume()` thread-safe state triggers on `ProcessCollector` and `FileCollector` to dynamically skip scans during LLM thinking. ProcessCollector now supports macOS and Linux (cross-platform fallback parsing unix `ps -eo pid,comm,args` output).
- `core_controller.py` — `setup_modules()`: registers `SecurityIntentParser` after news and file parsers.
- `core_controller.py` — `SYSTEM_PROMPT`: clarified that security mode is handled automatically by the plugin system (LLM does not need to append markers for it).

## [0.2.1] - 2026-06-04


### Changed (Architecture Refactoring — Extensibility & Responsiveness)
- **Extracted `CoreController`** (`current/core_controller.py`): unified business logic controller shared by both CLI and GUI. Encapsulates moral evaluation, memory retrieval, intent routing, vision routing, and Ollama fallback in a single `post_message()` method.
- **Introduced `IntentRouter`** (`current/intent_router.py`): ordered plugin registry that dispatches user messages to the first matching feature module via `should_parse() → parse_intent() → execute()`.
- **Added `ModuleResult` dataclass** to `base_intent_parser.py` as the standardised return type (`reply`, `articles`, `marker`) for all module plugins.
- **Added `execute()` abstract method** to `BaseIntentParser` — all feature parsers now implement the full plugin interface (`AlarmIntentParser`, `FileIntentParser`, `NewsIntentParser`).
- **Replaced `OllamaWorker` + `NewsWorker`** in `assistant_gui.py` with a single `ControllerWorker(QThread)` that runs `CoreController.post_message()` in the background. Emits `status_update` signal (`'typing'` | `'fetching_news'`) for context-aware GUI title labels.
- **Extracted `handle_memory_command()`** and `SYSTEM_PROMPT` from `assistant.py` to `core_controller.py` so CLI and GUI share a single source of truth.
- **Simplified `send_message()`** in `assistant_gui.py` from ~350 lines to ~120 lines: only system commands (exit / restart / update / /memory) run in the main thread; all other messages are delegated to `ControllerWorker`.
- **Simplified CLI loop** in `assistant.py`: system commands handled locally; normal messages call `controller.post_message()` directly.
- Alarm module's `_capture_llm` hack removed — alarm handler now calls `context["call_llm"]` synchronously inside the worker thread.

### Added
- `current/core_controller.py` — new unified controller module.
- `current/intent_router.py` — new plugin registry and dispatcher.
- `current/tests/test_router.py` — 8 unit tests covering `ModuleResult`, router registration ordering, match/no-match routing, and intent-fallthrough logic.

## [0.2.0] - 2026-06-03

### Added
- Implemented Phase 1 MVP of the AI Memory System (`current/memory_manager.py`) according to `AI_Memory_System_Design_v2.md` specifications.
- Implemented secure memory persistence under `memory/` using daily file slices (`YYYY-MM-DD_memory.json`), an `index.json` registry, and `filelock` for safe concurrent thread/process writes.
- Implemented robust JSON schema validation for all stored memory units (validating fields, category, confidence, and timestamps).
- Implemented keyword-based memory retrieval and scoring (incorporating recency and confidence weights) to inject top 5 context-relevant memories into Ollama prompts.
- Implemented dual-phase asynchronous background memory extraction (Phase 1: extracting facts on user input; Phase 2: extracting commitments/conclusions after assistant reply) in separate background threads.
- Added `/memory` conversational CLI & GUI commands (`list`, `add`, `edit`, `delete`, `on`, `off`) to allow full user control over stored memories.
- Created comprehensive unit test suite (`current/tests/test_memory.py`) verifying schema validation, retrieval scoring, concurrency locking, and extraction flows.

## [0.1.9] - 2026-06-02

### Added
- Implemented automatic inactivity timer in the chat window (`ChatWindow`) that collapses the chat interface back into the floating bubble mode after 3 minutes of user inactivity.
- Implemented a pink pulsing reply notification light (`new_reply_pending` with smooth `QTimer` animation loop) in the floating bubble (`FloatingBubble`) when Ann receives replies or update check results while in bubble mode.
- Optimized focus handling by preventing focus calls on hidden line edit widgets.
- Addressed boundary conditions: ensured alarm triggers reset/extend inactivity appropriately, and user clicks to expand or dismiss alarms correctly clear pulsing notification states.
- Created unit tests (`tests/test_gui_inactivity.py`) covering inactivity timer reset, timeout triggers, alarm interaction, and pulsing bubble states.

## [0.1.8] - 2026-05-29

### Added
- Implemented PyQt6 news card widgets (`NewsCardWidget` and `MessageBubble` integration) featuring a sleek overlay layout to render up to 10 articles in the chat window.
- Implemented background parallel image extraction and downloading using `ThreadPoolExecutor` inside `NewsWorker`/`NewsManager` to prevent GUI rendering latency.
- Added OpenGraph and Twitter image metadata parser fallbacks inside `ArticleExtractor`.
- Added local image caching under `scratch/news_images/` with automated cleanup.
- Added comprehensive unit tests for image extraction and parallel downloading.
- Optimizations: Filtered out redundant text list items in PyQt6 message bubbles, disabled horizontal scrollbars, and set layout size policies on card text to prevent horizontal overflow.
- Added 2-line title elision (using character weight) and custom styled hover tooltips (`QToolTip` styled to match dark mode) to view full titles.

## [0.1.7] - 2026-05-28

### Added
- Created design and implementation specification for the File Generation module ([file_generation_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/file_generation_spec.md)) to save AI-generated code blocks directly.
- Expanded Drag and Drop (DND) receiver file formats in [drag_drop_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/drag_drop_spec.md) to support HTML, XML, C, C++, Java, Shell, SQL, CSS, TS, TOML, and ENV formats.
- Formulated an implementation plan for custom code block rendering and file-saving dialogs in PyQt6.
- Implemented **Conversational File Generation & History Export (Option C)**: allows saving code blocks or exporting conversation history directly to the workspace via natural language dialogue.
- Implemented **Conversational Program Exit (LLM-Driven)**: allows Ann to say a warm goodbye and automatically shut down the program when detecting user exit/close intent.
- Implemented **Conversational Program Restart (LLM-Driven)**: enables Ann to say "see you in a moment" and reboot the application immediately (exit code `3` intercepted by launcher).
- Implemented **Conversational Program Update (LLM-Driven)**: prompts Ann to warmly say goodbye when the user confirms an update, perform the self-update process, and restart.
- Added comprehensive unit tests in `test_file_handler.py`, `test_conversational_exit.py`, and `test_conversational_update_flow.py` to cover these conversational flows.

## [0.1.6] - 2026-05-28

### Added
- Created design and implementation specification for the modular AI Engine and vision-aware dynamic model routing ([ai_engine_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/ai_engine_spec.md)).
- Formulated an implementation plan for refactoring Ollama calls into `ollama_client.py` and implementing client-side automatic vision model detection.

## [0.1.5] - 2026-05-28

### Added
- Implemented update self-test and automatic rollback (fail-safe) mechanism to prevent startup crashes.
- Added `--self-test` mode to `current/assistant.py` to verify config load and library imports on startup.
- Updated `updater.py` to run background self-test after file swapping, rolling back automatically to the previous backup in `versions/` if it fails.
- Enhanced `launcher.py` with a 10-second startup monitoring watchdog, triggering rollback and restarting the previous stable version if a startup crash occurs immediately after an update.
- Updated `update_flow_architecture.md` documentation and Mermaid diagrams to reflect the post-update self-test and rollback paths.
- Added unit tests in `current/tests/test_rollback.py` to cover rollback and self-test scenarios.

## [0.1.4] - 2026-05-28

### Added
- Created design and implementation specification for the Drag and Drop (DND) file attachment feature ([drag_drop_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/drag_drop_spec.md)).
- Formulated an implementation plan for DND event handling in the PyQt6/PySide6 GUI.

## [0.1.3] - 2026-05-27

### Added
- Implemented a premium, minimalist PyQt6/PySide6 graphical user interface (GUI) based on Scheme B.
- Created `current/assistant_gui.py` containing:
  - `FloatingBubble`: A draggable, circular, transparent floating widget named "Ann".
  - `ChatWindow`: A dark-themed frameless chat window with custom header, scrollable conversation, styled bubbles, and enter key bindings.
- Added automatic Dual-Mode Fallback: launches in GUI mode if PyQt6/PySide6 is available, but automatically downgrades to CLI mode if they are absent or if `--cli` is passed.
- Added `current/tests/test_gui_imports.py` to verify import and fallback mechanics.

## [0.1.2] - 2026-05-26

### Changed
- Aligned version checks to follow the new date+commit-SHA self-update flow (`YYYYMMDD-sha` format) instead of the GitHub Release Tag flow.
- Updated `current/version_check.py` to check branch commits on startup.
- Refactored `current/tests/test_version_check.py` to mock branch commit API responses.
- Fixed `launcher.py` to terminate the launcher process completely when the assistant exits cleanly (code 0) rather than restarting it.
- Documented current moral module implementation status and over-refusal limitations in `README.md`.

## [0.1.1] - 2026-05-26

### Changed
- Translated all Chinese content to English across `README.md` and `ai-assistant-design-notes.md`, including Mermaid diagram labels, tables, section headers, code comments, and prose.

### Added
- Implemented the full project codebase:
  - `launcher.py` — persistent process that monitors and restarts `assistant.py`; never auto-updated.
  - `updater.py` — downloads only `Ann/current/` via the GitHub Contents API, validates with `pytest`, performs atomic swap, and rolls back on failure.
  - `config.yml` — user configuration (Ollama + `gemma4:e4b`; `allowAutomaticMoralUpdates: false`).
  - `version.txt` — current version tracking.
  - `current/assistant.py` — CLI conversation loop with startup version check and moral evaluation on every message.
  - `current/version_check.py` — GitHub Releases API version comparison helper.
  - `current/moral_evaluator.py` — rule-based risk classifier implementing moral_module_spec.md §9–12.
  - `current/tests/test_moral_evaluator.py` — 22 test cases covering all risk levels and edge cases.
  - `current/tests/test_version_check.py` — 4 test cases with full mock coverage (network, disabled, up-to-date, update available).
- All 26 tests pass ✅.



## [0.1.0] - 2026-05-26

### Added
- Created a developer-friendly [README.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/README.md) organizing the project architecture, directory structure, and GitHub REST API self-updating flow.
- Configured a dedicated section for the **Moral & Safety Specification Module** based on [moral_module_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/moral_module_spec.md).
- Documented specific moral module rules (designed by OpenAI, audited by Claude, modification strictly prohibited) and their integration with the decision pipeline and update permissions.
- Named the AI Assistant **Ann**.
- Optimized the self-updating architecture design to use the GitHub Contents API to only download the `Ann/` subdirectory rather than the entire multi-project repository zipball.
- Created this [CHANGELOG.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/CHANGELOG.md) to track project development history.

