# 4×4 Rubik's Cube Simulator & Solver

An interactive 3D 4×4 Rubik's Cube (Rubik's Revenge) simulator with step-by-step tutorial solver, built with TypeScript, Vite, and Three.js.

## Features

- **3D Interactive View** — drag to rotate the cube view; touch-friendly for mobile browsers
- **Scramble** — randomizes the cube with 20 moves (animated, button locked during playback)
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

---

## Pending Work — v0.2.0

The following two problems are confirmed by the user and need to be fixed together.

### Problem 1 — Scramble has no animation

**Current behaviour**: `btnScramble` click in `main.ts` calls `scramble()` which computes the final
state instantly, then calls `renderer.updateState(state)` which replaces all sticker colours in one
frame. The cube appears to "jump" to a scrambled state with no physical motion.

**Required behaviour**:
- Generate 20 random moves (not 40).
- Play them one-by-one with the same per-move rotation animation as the solver.
- Lock (disable) the Scramble button for the entire duration; unlock when the last move finishes.

### Problem 2 — Solve animation jumps colours instead of rotating layers

**Current behaviour**: `TutorialPlayer` fires a `setTimeout` for each move. The `onStep` callback
in `main.ts` calls `applyMove(state, move)` then `renderer.updateState(state)`. `updateState`
removes all 96 sticker meshes from the scene and rebuilds them at fixed positions with new colours —
so the cube "snaps" rather than physically rotating a layer.

**Required behaviour**: Each move must visually rotate the corresponding layer of cubies around its
axis (e.g. U-move rotates the top 4×4 slice around the Y-axis by 90°, taking ~300 ms). Only after
the rotation animation completes should the sticker colours be updated and the next move begin.

---

## Architecture Change Required — Renderer Rewrite

`src/ui/Renderer.ts` must be rewritten with a **cubie-based architecture**.

### Key concepts

| Term | Meaning |
|---|---|
| Cubie | One of the 64 physical blocks. Each is a `THREE.Group` containing a black box body plus 1–3 coloured sticker planes. |
| Grid position | `(gx, gy, gz)` where each coordinate is 0–3. World position = `(coord − 1.5) × GAP`. |
| Layer | The set of cubies sharing one grid coordinate value on one axis (e.g. the U layer = all cubies where `gy === 3`). |

### Sticker colour lookup

Given a cubie at `(gx, gy, gz)` and a face direction, the index into `CubeState.stickers` is:

| Face | Condition | `stickers[face][idx]` |
|---|---|---|
| U (face 0) | `gy === 3` | `stickers[0][gz*4 + gx]` |
| D (face 1) | `gy === 0` | `stickers[1][(3-gz)*4 + gx]` |
| F (face 2) | `gz === 3` | `stickers[2][(3-gy)*4 + gx]` |
| B (face 3) | `gz === 0` | `stickers[3][(3-gy)*4 + (3-gx)]` |
| L (face 4) | `gx === 0` | `stickers[4][(3-gy)*4 + (3-gz)]` |
| R (face 5) | `gx === 3` | `stickers[5][(3-gy)*4 + gz]` |

### Grid position update after a CW rotation

After a layer is rotated 90° CW, each cubie in that layer gets new grid coordinates:

| Move axis | CW transform (for affected cubies) |
|---|---|
| U / Uw (Y-axis, layer `gy`) | `(gx, gy, gz)` → `(gz, gy, 3−gx)` |
| D / Dw (Y-axis, layer `gy`) | `(gx, gy, gz)` → `(3−gz, gy, gx)` |
| R / Rw (X-axis, layer `gx`) | `(gx, gy, gz)` → `(gx, gz, 3−gy)` |
| L / Lw (X-axis, layer `gx`) | `(gx, gy, gz)` → `(gx, 3−gz, gy)` |
| F / Fw (Z-axis, layer `gz`) | `(gx, gy, gz)` → `(3−gy, gx, gz)` |
| B / Bw (Z-axis, layer `gz`) | `(gx, gy, gz)` → `(gy, 3−gx, gz)` |

For `'` (CCW) moves apply the CW transform 3 times; for `2` moves apply twice.

### `playMove(move: MoveCode): Promise<void>`

This is the core new method. Steps:

1. Parse the move: extract base name and suffix (`'` / `2` / none).
2. Determine axis, rotation angle (`±π/2` or `π`), and which cubie grid indices belong to the layer(s).
3. Create a temporary `layerGroup = new THREE.Group()`.
4. **Re-parent** each layer cubie from `pivot` into `layerGroup` (preserving world position).
5. Add `layerGroup` to `pivot`.
6. Animate `layerGroup.rotation` from 0 to target angle using a `requestAnimationFrame` loop over ~300 ms.
7. After animation: re-parent each cubie back into `pivot`, update its `userData.gx/gy/gz`, set its `position` to `(gx−1.5)×GAP` etc.
8. Remove `layerGroup` from `pivot`.
9. Re-colour all sticker materials from the updated `CubeState`.
10. Resolve the Promise.

### Bug in `applyLayerU` — must fix

`src/cube/Moves.ts` `applyLayerU` calls `cycle4(...)` **and then** immediately repeats the same
cycle manually. This applies the U layer rotation twice per call, making every U move behave like
U2. Fix: **delete the `cycle4(...)` call** (lines 64–66) and keep only the manual section below it.

After fixing, run `npm test` to confirm all 16 tests still pass.

---

## Status

- v0.1.0 — Initial version (instant state-jump rendering)
- v0.2.0 — **In progress**: cubie-based animation, animated scramble, fix U-move bug
