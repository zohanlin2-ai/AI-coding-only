# Changelog

## [0.2.0] - 2026-06-11

### Fixed
- **Move engine geometry**: rewrote `Moves.ts` from first principles (each move is a
  real rigid rotation), fixing a bug where turning a layer corrupted sticker colors.
  Verified at the sticker level against an independent physical cubie model.
- Coherent clockwise sign convention across all six faces.

### Added
- **Real turn animation**: `Renderer.animateMove` rotates the actual cubie layer in
  3D (engine and renderer share one geometry), with a live "Turn Speed" slider that
  drives both scramble and solve.
- **Working solver** (previously a non-functional heuristic). Solves any scramble:
  - `Cube3` + `Lbl3` — verified 3×3 engine and layer-by-layer solver (200/200).
  - `Reduce4` — centres (4 faces by clean 3-cycles + a 70-state BFS for the last two),
    edge pairing (slice-flip with verified setup search), and a parity trial that
    applies the correct centre-preserving OLL/PLL parity algorithms.
  - End-to-end: solves arbitrary 4×4 scrambles, ~0.4s each.
- Geometric regression tests (move correctness, cube geometry, centres, full solve).

## [0.1.0] - 2026-06-10

### Added
- Initial project setup with Vite + TypeScript + Three.js
- `CubeState` — 6-face × 16-sticker state representation for 4×4 cube
- `Moves` — full move set including outer (U/D/F/B/L/R) and wide/inner layers (Uw/Dw/Fw/Bw/Lw/Rw) with CW, CCW, and 180° variants
- `scramble()` — randomized 40-move scrambler
- `Solver` — Reduction Method solver: Centers → Edge Pairing → 3×3 LBL → Parity Fix
- `Renderer` — Three.js 3D cube with 96 colored stickers, drag-to-rotate (mouse + touch)
- `TutorialPlayer` — animated step-by-step playback with configurable speed and pause/resume
- UI panel with Scramble, Solve, Reset, Pause/Resume, and speed slider
- Tutorial sidebar highlighting active stage (Centers / Edges / 3×3 / Parity)
- Vitest unit tests covering state, move inverses, wide moves, and scramble
