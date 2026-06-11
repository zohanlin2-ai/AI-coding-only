# 4×4 Rubik's Cube Simulator & Solver

An interactive 3D 4×4 Rubik's Cube (Rubik's Revenge) simulator with a step-by-step tutorial solver, built with TypeScript, Vite, and Three.js.

## Features

- **3D Interactive View** — drag to rotate the cube view; touch-friendly for mobile browsers
- **Animated Scramble** — randomizes the cube with 40 moves, played as real layer turns
- **Real Turn Animation** — every move physically rotates the affected layer of cubies in 3D
- **Step-by-Step Solver** — solves any scramble using the Reduction Method:
  1. Solve Centers (fix the 2×2 center blocks on each face)
  2. Pair Edges (group matching edge pairs)
  3. Fix Parity (handles OLL / PLL parity errors unique to 4×4)
  4. Solve as 3×3 (layer-by-layer: cross → corners → middle → last layer)
- **Turn Speed** — adjust the turn animation speed live via slider (scramble and solve)
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
│   └── Moves.ts      # Geometry-derived move engine (outer + wide/inner) + scramble
├── solver/
│   ├── Solver.ts     # Orchestrates the reduction: Centers → Edges → Parity → 3×3
│   ├── Reduce4.ts    # 4×4 reduction: centre solving + edge pairing
│   ├── Cube3.ts      # Standalone, verified 3×3 engine
│   └── Lbl3.ts       # Layer-by-layer 3×3 solver
├── ui/
│   ├── Renderer.ts   # Three.js renderer with animated layer turns + drag controls
│   └── Tutorial.ts   # Step-by-step move player with speed control
└── main.ts           # App entry point & UI wiring
tests/                # Vitest: move/geometry correctness, centres, full end-to-end solve
```

## Solving Method

The solver uses the **Reduction Method**:

1. **Centers** — Solve four faces with clean centre 3-cycles, then finish the last two
   (adjacent) faces with a small breadth-first search.
2. **Edges** — Pair the 12 dedges with the slice-flip technique: align two matching
   wings and apply a fixed merge algorithm (the last two edges use a dedicated alg).
3. **Parity** — Apply the centre-preserving OLL parity (flipped dedge) and/or PLL
   parity (swapped dedges) algorithms so the reduced cube becomes a solvable 3×3.
4. **3×3 Stage** — Treat the reduced cube as a 3×3 and solve it layer by layer.

Every move is verified against the engine, so the solver is robust to move-direction
conventions. It solves arbitrary scrambles in well under a second.

## Status

- v0.1.0 — Initial version (instant state-jump rendering, non-functional solver)
- v0.2.0 — Move engine fixed, real 3D turn animation, fully working solver (solves any scramble)
