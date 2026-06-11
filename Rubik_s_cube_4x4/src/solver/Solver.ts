import { CubeState } from '../cube/State.js';
import { MoveCode, applyMove } from '../cube/Moves.js';
import { Cube3 } from './Cube3.js';
import { solve3 } from './Lbl3.js';
import { reduceCenters, reduceEdges } from './Reduce4.js';

// Reduction-method solver for the 4x4:
//   1. Solve centres      2. Pair edges
//   3. Fix 4x4 parity     4. Solve the reduced cube as a 3x3
// Each stage returns the moves it used so the tutorial can play them back.

export interface SolveStep {
  label: string;
  moves: MoveCode[];
}

function applyMoves(state: CubeState, moves: MoveCode[]): CubeState {
  return moves.reduce((s, m) => applyMove(s, m), state);
}

// Project a reduced 4x4 onto a logical 3x3 (corners/edges/centres -> 3x3 cells).
export function read3x3(state: CubeState): Cube3 {
  const map = [0, 1, 3];
  const stickers: number[] = [];
  for (let f = 0; f < 6; f++)
    for (let R = 0; R < 3; R++)
      for (let C = 0; C < 3; C++)
        stickers[f * 9 + R * 3 + C] = state.get(f, map[R], map[C]);
  return new Cube3(stickers);
}

// 4x4 parity algorithms (centre- and pairing-preserving). OLL parity flips one
// dedge; PLL parity swaps two dedges. They map a reduced-but-unsolvable cube to
// a solvable one.
const OLL_PARITY = parse("Rw2 B2 U2 Lw U2 Rw' U2 Rw U2 F2 Rw F2 Lw' B2 Rw2");
const PLL_PARITY = parse("Rw2 R2 U2 Rw2 R2 Uw2 Rw2 R2 Uw2 U2");
function parse(s: string): MoveCode[] {
  return s.split(/\s+/) as MoveCode[];
}

// Solve the reduced cube as a 3x3. Tries the four parity combinations and keeps
// the one that fully solves (exactly one makes the projection a solvable 3x3).
function solveReducedAs3x3(state: CubeState): { parity: MoveCode[]; three: MoveCode[] } | null {
  const fixes: MoveCode[][] = [[], OLL_PARITY, PLL_PARITY, [...OLL_PARITY, ...PLL_PARITY]];
  for (const parity of fixes) {
    try {
      const test = applyMoves(state, parity);
      const three = solve3(read3x3(test)) as unknown as MoveCode[];
      if (applyMoves(test, three).isSolved()) return { parity, three };
    } catch {
      // invalid projection for this parity guess — try the next
    }
  }
  return null;
}

export function solve(state: CubeState): SolveStep[] {
  const steps: SolveStep[] = [];
  let current = state.clone();

  const centerMoves = reduceCenters(current);
  current = applyMoves(current, centerMoves);
  steps.push({ label: 'Solve Centers', moves: centerMoves });

  const edgeMoves = reduceEdges(current);
  current = applyMoves(current, edgeMoves);
  steps.push({ label: 'Pair Edges', moves: edgeMoves });

  const r = solveReducedAs3x3(current);
  if (r) {
    if (r.parity.length) {
      current = applyMoves(current, r.parity);
      steps.push({ label: 'Fix Parity', moves: r.parity });
    }
    steps.push({ label: 'Solve as 3×3', moves: r.three });
  }
  return steps;
}
