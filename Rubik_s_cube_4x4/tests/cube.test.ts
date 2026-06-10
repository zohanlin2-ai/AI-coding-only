import { describe, it, expect } from 'vitest';
import { CubeState } from '../src/cube/State.js';
import { applyMove, applyMoves, scramble, MoveCode } from '../src/cube/Moves.js';

describe('CubeState', () => {
  it('starts solved', () => {
    expect(new CubeState().isSolved()).toBe(true);
  });

  it('clone is independent', () => {
    const a = new CubeState();
    const b = a.clone();
    b.stickers[0][0] = 3;
    expect(a.stickers[0][0]).toBe(0);
  });
});

describe('Moves', () => {
  it('U then U\' returns to solved', () => {
    let s = new CubeState();
    s = applyMove(s, 'U');
    s = applyMove(s, "U'");
    expect(s.isSolved()).toBe(true);
  });

  it('U4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'U');
    expect(s.isSolved()).toBe(true);
  });

  it('R4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'R');
    expect(s.isSolved()).toBe(true);
  });

  it('F4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'F');
    expect(s.isSolved()).toBe(true);
  });

  it('L4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'L');
    expect(s.isSolved()).toBe(true);
  });

  it('D4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'D');
    expect(s.isSolved()).toBe(true);
  });

  it('B4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'B');
    expect(s.isSolved()).toBe(true);
  });

  it('Rw4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'Rw');
    expect(s.isSolved()).toBe(true);
  });

  it('Uw4 returns to solved', () => {
    let s = new CubeState();
    for (let i = 0; i < 4; i++) s = applyMove(s, 'Uw');
    expect(s.isSolved()).toBe(true);
  });

  it('U2 is same as U U', () => {
    const a = applyMoves(new CubeState(), ['U', 'U']);
    const b = applyMove(new CubeState(), 'U2');
    expect(a.stickers).toEqual(b.stickers);
  });

  it('R then R\' is identity', () => {
    const s = applyMoves(new CubeState(), ['R', "R'"]);
    expect(s.isSolved()).toBe(true);
  });

  it('scramble produces non-solved state', () => {
    const { state } = scramble(new CubeState(), 20);
    expect(state.isSolved()).toBe(false);
  });

  it('scramble move list has correct length', () => {
    const { moves } = scramble(new CubeState(), 30);
    expect(moves).toHaveLength(30);
  });

  it('applying inverse of each move class solves it', () => {
    const pairs: [MoveCode, MoveCode][] = [
      ['F', "F'"], ['B', "B'"], ['L', "L'"],
      ['Fw', "Fw'"], ['Bw', "Bw'"], ['Lw', "Lw'"],
      ['Dw', "Dw'"],
    ];
    for (const [m, inv] of pairs) {
      const s = applyMoves(new CubeState(), [m, inv]);
      expect(s.isSolved()).toBe(true);
    }
  });
});
