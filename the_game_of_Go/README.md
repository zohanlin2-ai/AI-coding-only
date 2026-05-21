# 碁 Go App (The Game of Go)

A premium, highly-responsive, and modern web-based Go (圍棋) board game application built with React, Vite, and TypeScript. The application supports multiple board sizes, rule variants, handicap placements, SGF file serialization/deserialization, and intelligent cloud LLM AIs as well as a local fallback heuristic AI.

## Key Features

- **Multiple Board Sizes**: Support for standard **9x9** (for beginners/quick games), **13x13** (for tactical exercises), and **19x19** (for standard full games).
- **Rule Configurations**: Toggle between **Chinese Rules** (Area Scoring / 數子法) and **Japanese Rules** (Territory Scoring / 比目法) before starting a game.
- **Handicap Stone Placement**: Choose from 2 to 9 handicap stones. Features a live visual mini-preview showing the exact star point configurations.
- **Advanced AI Integration**:
  - Independent AI toggle for both Black and White players (players can be Human vs. Human, Human vs. AI, or AI vs. AI).
  - Multiple API choices: **Gemini AI** (default Gemini 2.5 Flash), **Groq AI** (open-source high-speed models like Llama 3.3), and **OpenRouter AI** (free-tier models).
  - **Local Heuristic AI**: A custom offline heuristic-based decision engine that requires no internet connection or API keys.
  - Safe LLM coordinate wrapping: The app generates a dynamic list of valid legal move coordinates for the LLM to select, preventing illegal move attempts.
- **Interactive Scoring HUD**:
  - Automatically triggers at consecutive passes (2 passes) or resignation.
  - Displays territory overlays directly on the board.
  - Users can interactively click stones to toggle their "Dead/Alive" state, immediately updating the score.
  - Clear, mathematical scoring breakdown explaining exactly how the score was calculated (including active stones count, territory count, prisoners count, and Komi).
- **SGF Import & Export**: Fully supports saving games to standard `.sgf` files or uploading existing ones to continue play or study.
- **tactile UI/UX & High-DPI Support**:
  - Custom dark theme with glassmorphic control panels.
  - A tactile Kaya-wood board texture and radial 3D stone gradients mimicking slate and shell stones.
  - High-DPI retina display scaling on the canvas prevents coordinate text or line blurring.

## Technology Stack

- **Core Framework**: React 19, TypeScript 6
- **Build Tool**: Vite 8
- **Styling**: Vanilla CSS (specifically tailored custom glassmorphism and modern colors)
- **Testing**: Vitest for test-driven logic verification

---

## Project Structure

```
├── public/                 # Static assets
├── src/
│   ├── assets/             # Images and design assets
│   ├── components/
│   │   ├── GoBoard.tsx     # High-DPI HTML5 canvas Go board with interactive overlays
│   │   └── SetupPanel.tsx  # Game configuration page (board sizes, rules, handicap, AIs)
│   ├── services/
│   │   └── aiService.ts    # Heuristic AI and cloud LLM (Gemini/Groq/OpenRouter) integration
│   ├── utils/
│   │   ├── goEngine.ts     # Core Go rules engine (liberties, capture, suicide, Ko, scoring)
│   │   ├── goEngine.test.ts# Vitest unit test suite
│   │   └── sgfParser.ts    # SGF importer/exporter serialization
│   ├── App.css             # Component-level styles
│   ├── App.tsx             # Main game state orchestration container
│   ├── index.css           # Global custom theme & design tokens
│   ├── main.tsx            # Application entrypoint
│   └── vite-env.d.ts
├── package.json
├── tsconfig.json
└── README.md
```

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher recommended)
- [npm](https://www.npmjs.com/) (installed automatically with Node.js)

### Installation

1. Clone or download the repository to your local machine.
2. Open your terminal in the project root directory.
3. Install dependencies:
   ```bash
   npm install
   ```

### Running Locally

To launch the local development server:
```bash
npm run dev
```
Once started, the terminal will display a local address (usually `http://localhost:5173`). Open this URL in your web browser to play!

### Running Tests

To run the unit test suite and verify Go rules engine accuracy (captures, suicide prevention, Ko rule, scoring, etc.):
```bash
npm run test
```

### Production Build

To compile and bundle the application for production deployment:
```bash
npm run build
```
The compiled files will be output to the `dist/` directory, ready to be served offline or uploaded to any static hosting provider.
