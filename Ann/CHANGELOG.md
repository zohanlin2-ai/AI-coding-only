# Changelog

All notable changes to the **Ann** AI assistant project will be documented in this file.

## [0.1.2] - 2026-05-26

### Changed
- Aligned version checks to follow the new date+commit-SHA self-update flow (`YYYYMMDD-sha` format) instead of the GitHub Release Tag flow.
- Updated `current/version_check.py` to check branch commits on startup.
- Refactored `current/tests/test_version_check.py` to mock branch commit API responses.
- Fixed `launcher.py` to terminate the launcher process completely when the assistant exits cleanly (code 0) rather than restarting it.

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

