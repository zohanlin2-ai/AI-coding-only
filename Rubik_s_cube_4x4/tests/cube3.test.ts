import { describe, it, expect } from 'vitest';
import { Cube3, applyMove3, scramble3, Move3, ALL_MOVES3 } from '../src/solver/Cube3.js';

// Independent physical cubie oracle for the 3x3 engine (same idea as the 4x4
// move_correctness test): rotate cubies + their sticker directions in 3D.
type Vec = [number, number, number];
type Dir = 'PX' | 'NX' | 'PY' | 'NY' | 'PZ' | 'NZ';
const DV: Record<Dir, Vec> = { PX: [1, 0, 0], NX: [-1, 0, 0], PY: [0, 1, 0], NY: [0, -1, 0], PZ: [0, 0, 1], NZ: [0, 0, -1] };
const toDir = (v: Vec): Dir => {
  const r = v.map(c => Math.round(c)) as Vec;
  return (Object.keys(DV) as Dir[]).find(d => DV[d].every((e, i) => e === r[i]))!;
};
const rot = (v: Vec, a: 'x' | 'y' | 'z', deg: number): Vec => {
  const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t); const [x, y, z] = v;
  if (a === 'x') return [x, y * c - z * s, y * s + z * c];
  if (a === 'y') return [x * c + z * s, y, -x * s + z * c];
  return [x * c - y * s, x * s + y * c, z];
};
function slot(face: number, row: number, col: number) {
  switch (face) {
    case 0: return { x: col, y: 2, z: row, d: 'PY' as Dir };
    case 1: return { x: col, y: 0, z: 2 - row, d: 'NY' as Dir };
    case 2: return { x: col, y: 2 - row, z: 2, d: 'PZ' as Dir };
    case 3: return { x: 2 - col, y: 2 - row, z: 0, d: 'NZ' as Dir };
    case 4: return { x: 0, y: 2 - row, z: 2 - col, d: 'NX' as Dir };
    default: return { x: 2, y: 2 - row, z: col, d: 'PX' as Dir };
  }
}
const TURN: Record<string, { axis: 'x' | 'y' | 'z'; sign: number; layer: number }> = {
  U: { axis: 'y', sign: -1, layer: 2 }, D: { axis: 'y', sign: 1, layer: 0 },
  F: { axis: 'z', sign: -1, layer: 2 }, B: { axis: 'z', sign: 1, layer: 0 },
  L: { axis: 'x', sign: 1, layer: 0 }, R: { axis: 'x', sign: -1, layer: 2 },
};
function physical(cube: Cube3, move: Move3): number[] {
  const base = move.replace(/['2]/, ''); const suf = move.slice(base.length);
  const info = TURN[base]; const times = suf === "'" ? 3 : suf === '2' ? 2 : 1;
  const ck = (x: number, y: number, z: number) => `${x},${y},${z}`;
  let store = new Map<string, Partial<Record<Dir, number>>>();
  for (let f = 0; f < 6; f++) for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const sp = slot(f, r, c); const k = ck(sp.x, sp.y, sp.z);
    if (!store.has(k)) store.set(k, {});
    store.get(k)![sp.d] = cube.get(f, r * 3 + c);
  }
  for (let t = 0; t < times; t++) {
    const next = new Map<string, Partial<Record<Dir, number>>>();
    const coord = (x: number, y: number, z: number) => info.axis === 'x' ? x : info.axis === 'y' ? y : z;
    for (const [k, st] of store) {
      const [x, y, z] = k.split(',').map(Number);
      if (coord(x, y, z) !== info.layer) { next.set(k, { ...st }); continue; }
      const p = rot([x - 1, y - 1, z - 1], info.axis, info.sign * 90);
      const nk = ck(Math.round(p[0] + 1), Math.round(p[1] + 1), Math.round(p[2] + 1));
      const m = next.get(nk) ?? {};
      for (const d of Object.keys(st) as Dir[]) m[toDir(rot(DV[d], info.axis, info.sign * 90))] = st[d]!;
      next.set(nk, m);
    }
    store = next;
  }
  const out = new Array(54).fill(-1);
  for (let f = 0; f < 6; f++) for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const sp = slot(f, r, c); out[f * 9 + r * 3 + c] = store.get(ck(sp.x, sp.y, sp.z))![sp.d];
  }
  return out;
}

describe('Cube3 engine', () => {
  for (const m of ALL_MOVES3) {
    it(`${m} matches the physical model`, () => {
      const uniq = new Cube3(Array.from({ length: 54 }, (_, i) => i));
      expect(applyMove3(uniq, m).stickers).toEqual(physical(uniq, m));
    });
  }
  it('scramble + exact reverse solves', () => {
    const inv = (m: Move3): Move3 => (m.endsWith('2') ? m : m.endsWith("'") ? m.slice(0, -1) : m + "'") as Move3;
    for (let t = 0; t < 20; t++) {
      const { cube, moves } = scramble3(30);
      let c = cube.clone();
      for (let i = moves.length - 1; i >= 0; i--) c = applyMove3(c, inv(moves[i]));
      expect(c.isSolved()).toBe(true);
    }
  });
});
