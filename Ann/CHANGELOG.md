# Changelog

All notable changes to the **Ann** AI assistant project will be documented in this file.

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

