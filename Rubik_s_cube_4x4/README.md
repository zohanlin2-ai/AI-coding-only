# 4×4 Rubik's Cube Simulator & Solver

An interactive 3D 4×4 Rubik's Cube (Rubik's Revenge) simulator with step-by-step tutorial solver, built with TypeScript, Vite, and Three.js.

## Features

- **3D Interactive View** — drag to rotate the cube view; touch-friendly for mobile browsers
- **Scramble** — randomizes the cube with 40 moves
- **Step-by-Step Solver** — animated solution using the Reduction Method:
  1. Solve Centers (fix the 2×2 center blocks on each face)
  2. Pair Edges (group matching edge pairs)
  3. Solve as 3×3 (LBL: Cross → F2L → OLL → PLL)
  4. Fix Parity (handles OLL and PLL parity errors unique to 4×4)
- **Speed Control** — adjust animation speed via slider
- **Tutorial Panel** — highlights the current stage and shows the full move sequence
- **Pause / Resume** — pause playback at any step to study the state

## Tech Stack

| Tool | Purpose |
|---|---|
| TypeScript | Type-safe logic |
| Vite | Build & dev server |
| Three.js | 3D rendering |
| Vitest | Unit tests |

## Getting Started

```bash
npm install
npm run dev      # development server
npm run build    # production build
npm test         # run tests
```

## Project Structure

```
src/
├── cube/
│   ├── State.ts      # 6×16 sticker representation
│   └── Moves.ts      # All moves (outer + wide/inner layers) + scramble
├── solver/
│   └── Solver.ts     # Reduction method solver (Centers → Edges → 3×3 → Parity)
├── ui/
│   ├── Renderer.ts   # Three.js 3D cube renderer with drag controls
│   └── Tutorial.ts   # Step-by-step move player with speed control
└── main.ts           # App entry point & UI wiring
tests/
└── cube.test.ts      # Unit tests for state and move correctness
```

## Solving Method

The solver uses the **Reduction Method**:

1. **Centers** — Place the four inner stickers on each face using commutator sequences
2. **Edges** — Pair edge pieces using Rw/Uw wide-move algorithms
3. **3×3 Stage** — Treat the reduced cube as a 3×3 and apply LBL
4. **Parity** — Fix OLL parity (flipped edge pair) or PLL parity (swapped edges) with dedicated algorithms

## Status

Initial version — v0.1.0
