# Changelog

All notable changes to the **Ann** AI assistant project will be documented in this file.

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

