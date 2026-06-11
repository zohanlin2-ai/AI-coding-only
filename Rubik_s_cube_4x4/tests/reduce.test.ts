import { describe, it, expect } from 'vitest';
import { CubeState } from '../src/cube/State.js';
import { applyMoves, scramble } from '../src/cube/Moves.js';
import { reduceCenters } from '../src/solver/Reduce4.js';

const CENTER_IDX = [5, 6, 9, 10];
const centersSolved = (c: CubeState) =>
  [0, 1, 2, 3, 4, 5].every(f => CENTER_IDX.every(i => c.stickers[f][i] === f));

describe('reduction: centres', () => {
  it('solves all six centres on 30 random scrambles', () => {
    let ok = 0;
    for (let t = 0; t < 30; t++) {
      const { state } = scramble(new CubeState(), 40);
      const moves = reduceCenters(state);
      if (centersSolved(applyMoves(state, moves))) ok++;
    }
    expect(ok).toBe(30);
  });
});
