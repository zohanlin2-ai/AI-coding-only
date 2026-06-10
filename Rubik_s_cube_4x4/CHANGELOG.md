# Changelog

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
