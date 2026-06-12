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

## Developer Notes — The "Turn Corrupts Colors" Bug (read before extending)

This is the single most important pitfall in this project. **Lock the move engine
down with the test below before building anything on top of it** (solver, animation,
larger cubes). A solved/uniform cube hides this class of bug — it only appears once
the cube is non-uniform (scrambled).

### Symptom

After rotating a single layer, some stickers show the **wrong color** — the cube
"jumps" to a state that is not a valid single turn. Looks fine on a solved cube,
breaks as soon as it is scrambled.

### Root cause (two independent layers)

1. **Geometrically inconsistent move engine.** The layer-cycling logic permuted the
   side stickers in a way that did not *compose* like a real cube. Order-based tests
   (`U⁴ = identity`, `U` then `U'` = identity) pass for *any* labeling, so they never
   catch it. The giveaway: the **"sexy move" `(R U R' U')` must have order 6** on a
   real cube — the broken engine gave 105. Also, all *adjacent* face-pairs are
   conjugate under a cube symmetry, so `R U`, `F R`, `U R` … must **share the same
   order**; a mismatch means an incoherent clockwise convention across faces.

2. **Facelet key collision.** The engine computes a move as "rotate each sticker's 3D
   point, look up which slot it lands in". Two stickers meeting at a **shared cube
   edge** (e.g. U's front row and F's top row) were given the **same 3D key** because
   the point was placed at `normal×1.5 + tangential`, where the tangential max (1.5)
   equals the normal offset. The lookup map overwrote one with the other, so moved
   stickers were sent to the wrong slots.

### The fix

1. Rebuild every move **from cube geometry**: a move is literally a rigid 90° rotation
   mapping surface sticker positions to positions. Use a **coherent clockwise sign**
   across all six faces (−90° about each outward normal).
2. Put the lookup key at `normal×2` (any offset **greater than** the tangential max of
   1.5) so edge-sharing facelets stay distinct points; use `normal×1.5` only for the
   separate "which cubie layer" test. See `KEY_SCALE` / `CUBIE_SCALE` in `Moves.ts`.

### How to catch it — verification that actually works

Order-based invariants are **not enough**. The decisive test is a **sticker-level
move-correctness test against an independent model** — a physical cubie model that
rotates the 4×4×4 cubies *and their sticker directions* in 3D (a completely different
algorithm from the engine's permutation). For every move, assert:

- every sticker that **should** move lands in the **correct** position, **and**
- every sticker **outside** the turned layer is **unchanged**, **and**
- the move is a **bijection** (no color lost or duplicated).

This lives in `tests/move_correctness.test.ts` and found the bug instantly (36/36
moves failed). Back it up with real-cube identities in `tests/geometry.test.ts`
(sexy move = order 6; all adjacent face-pairs share order 105). Run:

```bash
npm test     # tests/move_correctness.test.ts + tests/geometry.test.ts must be green
```

If those are green, the engine is trustworthy and higher-level features can build on it.

## Status

- v0.1.0 — Initial version (instant state-jump rendering, non-functional solver)
- v0.2.0 — Move engine fixed, real 3D turn animation, fully working solver (solves any scramble)
