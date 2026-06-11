import { describe, it, expect } from 'vitest';
import { CubeState } from '../src/cube/State.js';
import { applyMove, applyMoves, scramble, MoveCode } from '../src/cube/Moves.js';

// These check that moves compose like a real, coherently-oriented cube — the
// kind of geometric bug that order-2/order-4 invariants alone cannot catch.
function order(seq: MoveCode[], max = 5000): number {
  let s = new CubeState();
  for (let n = 1; n <= max; n++) { s = applyMoves(s, seq); if (s.isSolved()) return n; }
  return -1;
}

describe('cube geometry', () => {
  it('sexy move (R U R\' U\') has order 6', () => {
    expect(order(["R", "U", "R'", "U'"])).toBe(6);
  });

  it('(R U2 R\' U2) has order 15', () => {
    expect(order(["R", "U2", "R'", "U2"])).toBe(15);
  });

  // Any two adjacent face quarter-turns are conjugate under a cube symmetry,
  // so they must all share the same order. A mismatch means incoherent moves.
  it('all adjacent face-pairs share order 105', () => {
    const pairs: MoveCode[][] = [
      ["R", "U"], ["U", "R"], ["F", "R"], ["L", "D"], ["U", "F"], ["B", "L"],
    ];
    for (const p of pairs) expect(order(p)).toBe(105);
  });

  it('a pure inner slice (Rw R\') has order 4', () => {
    expect(order(["Rw", "R'"])).toBe(4);
  });

  it('scramble followed by its exact reverse returns to solved', () => {
    const inv = (m: MoveCode): MoveCode =>
      (m.endsWith('2') ? m : m.endsWith("'") ? m.slice(0, -1) : m + "'") as MoveCode;
    for (let t = 0; t < 20; t++) {
      const { state, moves } = scramble(new CubeState(), 30);
      let s = state.clone();
      for (let i = moves.length - 1; i >= 0; i--) s = applyMove(s, inv(moves[i]));
      expect(s.isSolved()).toBe(true);
    }
  });
});
