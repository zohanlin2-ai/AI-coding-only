# CHANGELOG.md

## [1.4.0] - 2026-05-22

### Added
- **Ollama Local AI Integration**:
  - Integrated local Ollama models (defaulting to `gemma4:latest`) in the backend request pipeline.
  - Added Ollama connection verification and status tracking in the UI.
  - Optimized local model queries with a 120-second timeout, 1024 max tokens, and disabled thinking mode (`extra_body={"think": False}`) for direct replies.
- **Post-Dialogue State Machine**:
  - Implemented 5 post-dialogue options (continue/restart with or without parameter adjustments, or end session) displayed when dialogue halts or times out.
- **Andrej Karpathy Guidelines**:
  - Formally documented the coding guidelines in `CLAUDE.md`.

### Fixed
- **Parameter Synchronization**:
  - Added synchronization logic so that editing after dialogue preserves the actual latest configuration instead of reverting to default values.

## [1.3.1] - 2026-05-22

### Fixed
- **UI Reset Behavior**:
  - Added programmatic reset of the "👥 參與 AI 數量" (Number of AI Agents) slider widget to its default value of `2` when the conversation terminates (either via manual stop or time expiration).

## [1.3.0] - 2026-05-22

### Added
- **Groq Cloud Integration**:
  - Integrated Groq Cloud API provider in backend model request pipeline (`gemma2-9b-it`, `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`).
  - Added Groq API key input, Console link, and synchronous key verification button in the UI.
  - Added Groq connection status indicator in the sidebar.
  - Supported Groq as a candidate coordinator in Orchestrator Mode.
  - Added comprehensive unit tests for Groq API client calls and key verification.
- **GitHub Models Integration**:
  - Integrated GitHub Models API provider in backend model request pipeline (`gpt-4o-mini`, `gpt-4o`, `meta-llama-3.1-8b-instruct`, `cohere-command-r-plus`).
  - Added GitHub Token/PAT input, settings link, and synchronous key verification button in the UI.
  - Added GitHub Models connection status indicator in the sidebar.
  - Supported GitHub Models as a candidate coordinator in Orchestrator Mode.
  - Added comprehensive unit tests for GitHub Models API client calls and token verification.

## [1.2.0] - 2026-05-22

### Added
- **Grok AI Integration**:
  - Integrated xAI's Grok API provider in backend model request pipeline (`grok-2-1212`, `grok-beta`).
  - Added Grok API key input, Console link, and synchronous key verification button in the UI.
  - Added Grok connection status indicator in the sidebar.
  - Supported Grok as a candidate coordinator in Orchestrator Mode.
  - Added comprehensive unit tests for Grok API client calls and key verification.
- **Model Provider Attribution**:
  - Annotated dialogues in the chat UI, typing indicator, review panel, and exported Markdown files to explicitly show which AI provider generated the message (e.g. `來自 OpenAI` or `來自 Grok`).
- **Dynamic Provider Filtering**:
  - Implemented dynamic model provider list filtering in the setup panel selectbox. If a provider's key verification fails, that provider is hidden from options. If it was already selected, it automatically falls back to `Mock` mode safely.

## [1.1.0] - 2026-05-22

### Added
- **API Key Verification**:
  - Added synchronous API Key validation for Gemini, OpenAI, Claude, and DeepSeek.
  - Interactive "驗證金鑰" (Verify Key) buttons under each API key input field in the Streamlit sidebar.
  - Implemented automated state transition resetting verification status to "unverified" if any key is edited.
  - Enhanced "API 連線狀態" (API Status) indicators displaying "🟢 驗證成功" (Verified), "🔴 未配置" (Not Configured), "🟡 已配置 (未驗證)" (Configured but Unverified), or "❌ 驗證失敗" (Verification Failed) with detailed error capture messages.
  - Added unit tests for key verification logic in `test_app.py`.

## [1.0.0] - 2026-05-22

### Added
- **Core Functionality**:
  - Multi-agent dialogue support for 1 to 4 AI agents.
  - Interactive UI built with Streamlit.
  - Custom topic configuration and dynamic role definitions for each agent.
  - Standard LLM API clients integrated for Google Gemini, OpenAI, Anthropic Claude, and DeepSeek.
  - Offline Mock AI simulation mode with a dynamic, randomized combination template generator.
  - Real-time countdown timer (1 to 120 minutes) with pacing control (1 to 15 seconds) and a manual stop button.
  - Selection of three turn-taking modes: Sequential (輪流), Nomination (點名接力), and Orchestrator (中央協調).
  - Randomizer fallback logic: Fills empty name, role, and topic fields with random presets in Chinese. Added "Randomize Blanks" and "Randomize All" buttons.
  - Markdown transcript download/export featuring the topic, participant configuration (name, role, model), and speaker-demarcated chat history.
- **Testing**:
  - Automated unit test suite `test_app.py` covering Mock AI generator, randomizer fallbacks, regular expression nomination parsing, turn-taking orchestration logic, transcript format schemas, and mock client integrations.
- **Developer Assets**:
  - Created `CLAUDE.md` to follow `andrej-karpathy-skills` rules.
  - Created `requirements.txt` and `README.md`.
