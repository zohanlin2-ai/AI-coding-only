# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-05-21

### Added
- **OpenAI GPT & Anthropic Claude Integration (Option A)**:
  - Direct integration with OpenAI REST API and Anthropic Claude messages API, with full JSON response parsing support.
  - Added an expandable Custom API Proxy URL input field for both Black and White setups to easily bypass client-side CORS issues.
  - Implemented Key Verification support (`validateApiKey`) for OpenAI and Anthropic API keys.
  - Automatically loads and saves OpenAI/Anthropic API keys and proxy configurations inside browser `localStorage`.
- **Pure TS Monte Carlo Tree Search Engine (Option B)**:
  - Implemented an offline-friendly, zero-dependency Monte Carlo Tree Search (MCTS) engine.
  - Combined MCTS selection with progressive bias using heuristic scores to boost intelligence and prevent tactical blunders.
  - Biased rollout simulations towards capturing moves to raise tactical depth.
  - Scaled iterations dynamically per board size to guarantee execution times of under 1-2 seconds.
- **UML Architecture Diagrams (uml.html)**:
  - Created a premium standalone HTML/CSS page featuring Mermaid.js Sequence and Activity diagrams.
  - All diagrams translated strictly to English and pre-loaded in a single view to prevent `display: none` rendering bugs.
  - Sequence diagram details the asynchronous user loop, rule validation, and AI dispatch.
  - Added an Activity diagram visualizing the entire application lifecycle, from game configuration, key/proxy validation, move loops, up to scoring rules and SGF exports.
  - Retained the Activity diagram detailing the Monte Carlo Tree Search (MCTS) offline AI engine search phases.
  - Built-in 2x supersampled high-res PNG export and lossless SVG vector file downloader using client-side XMLSerializer and Canvas APIs.
- **Testing & Verification**:
  - Expanded `simulateGame.test.ts` to include a full 9x9 MCTS AI vs MCTS AI game simulation, running all UCT tree search iterations and validating correctness.

## [1.1.0] - 2026-05-21

### Added
- **Natural AI Passing & Endgame Behavior (`aiService.ts`)**:
  - Implemented a BFS-based empty region size calculator to identify connected empty intersections.
  - Added an endgame detector that activates when empty board intersections fall below 35%.
  - Added dynamic region-size thresholds to penalize playing inside settled territories (wasting moves in own territories or making doomed invasions in opponent territories) while allowing normal opening/midgame plays and valid invasions.
  - Ensured both AI players naturally fill neutral points (Dame) and consecutively PASS once all boundaries are settled.
  - Added automated game simulation tests (`simulateGame.test.ts`) that play out complete games to verify the natural flow and scoring.

## [1.0.0] - 2026-05-21

### Added
- **Core Go Engine (`goEngine.ts`)**:
  - Full board size customization (9x9, 13x13, 19x19).
  - Accurate capture group verification based on liberties.
  - Suicide-prevention rules (legal only if it captures adjacent opponent group).
  - Ko rule enforcement comparing the simulated board hash with the state from two moves prior.
  - Chinese Area Scoring (数子法) calculating alive stones + surrounded territory.
  - Japanese Territory Scoring (比目法) calculating territory - prisoners (captured stones + dead stones remaining).
- **Tactile Go Board Component (`GoBoard.tsx`)**:
  - Interactive HTML5 Canvas scaled using `devicePixelRatio` for high-DPI displays.
  - Interactive hover stone previews, last move indicator rings, and translucent scoring territory overlays.
  - Manual toggle of dead stones during scoring mode.
- **Game Setup Interface (`SetupPanel.tsx`)**:
  - Pre-game configuration for rules, size, handicap stones, and player modes.
  - Interactive 3x3 star point mini-preview indicating where handicap stones will land.
  - Independent player controllers for Black and White (Human / AI).
  - API provider forms for Gemini, Groq, and OpenRouter, with key serialization to `localStorage`.
  - **Dynamic API Key Validation UI**: A new verification button next to the input fields to test keys on the fly before launching the game.
- **SGF File Parser (`sgfParser.ts`)**:
  - Full serialization of game variables, setup, and move sequences to standard Smart Game Format (SGF).
  - Safe parsing of `.sgf` files to reload active games or replays.
- **AI Integration Engine (`aiService.ts`)**:
  - Local heuristic offline evaluator assessing capture opportunities, self-preservation, edge penalties, star point preferences, and friendly stone connectivity.
  - LLM prompts listing only legal coordinates to guarantee 100% legal moves from Gemini 2.5 Flash, Groq, and OpenRouter.
  - **Live Verification Endpoint Utilities**: Performs lightweight GET requests (e.g. models list or key auth info checks) to verify Gemini, Groq, and OpenRouter API credentials without using generation token budgets.
- **Unit Testing Suite (`goEngine.test.ts`)**:
  - Comprehensive unit tests covering board initialization, liberty calculations, captures, suicide prevention, Ko rule enforcement, and scoring logic under Chinese vs. Japanese rules.
- **Visual Design**:
  - Radial-gradient wood grain board textures.
  - Radial slate/shell 3D shadow gradients on stone placement.
  - Glassmorphic layouts, status displays, and modern styling tokens in `index.css`.

### Optimized
- **AI Latency & Reliability (`aiService.ts`)**:
  - Restored `"thought"` to be generated first in the JSON response schema to preserve the intelligence of Chain-of-Thought (CoT) reasoning, but limited the output strictly to under 100 characters in traditional Chinese to keep token generation latency low.
  - Introduced a 12-second fetch timeout using `AbortController`. If a cloud LLM provider is congested or stalls, the request is aborted and automatically falls back to the Local Heuristic engine, preventing the game from freezing.

### Fixed
- **AI Game Loop Hang (`App.tsx`)**:
  - Resolved a React `useEffect` race condition where having `isAiThinking` in the dependency array triggered an immediate cleanup on state-render, clearing the scheduled timeout and causing the AI to remain permanently stuck in "AI thinking" state.
