import { describe, it, expect } from 'vitest';
import { CubeState } from '../src/cube/State.js';
import { applyMoves, scramble } from '../src/cube/Moves.js';
import { solve } from '../src/solver/Solver.js';

describe('solver', () => {
  it('returns no moves for an already-solved cube', () => {
    const total = solve(new CubeState()).reduce((n, s) => n + s.moves.length, 0);
    expect(total).toBe(0);
  });

  it('solves arbitrary 4x4 scrambles end to end', () => {
    let solved = 0;
    for (let t = 0; t < 25; t++) {
      const { state } = scramble(new CubeState(), 40);
      let s = state.clone();
      for (const step of solve(state)) s = applyMoves(s, step.moves);
      if (s.isSolved()) solved++;
    }
    expect(solved).toBe(25);
  }, 60000);
});
