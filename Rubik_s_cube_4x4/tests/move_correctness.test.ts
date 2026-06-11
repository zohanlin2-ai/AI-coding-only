import { describe, it, expect } from 'vitest';
import { CubeState } from '../src/cube/State.js';
import { applyMove, TURN_INFO, MoveCode } from '../src/cube/Moves.js';

// Independent "physical" oracle: model the cube as 4x4x4 cubies, each carrying
// outward-facing stickers. A move physically rotates a slab of cubies AND
// reorients their sticker directions. This is a different algorithm from the
// engine's position->slot permutation, so agreement validates the engine.

type Vec = [number, number, number];
type DirName = 'PX' | 'NX' | 'PY' | 'NY' | 'PZ' | 'NZ';
const DIR_VEC: Record<DirName, Vec> = {
  PX: [1, 0, 0], NX: [-1, 0, 0], PY: [0, 1, 0], NY: [0, -1, 0], PZ: [0, 0, 1], NZ: [0, 0, -1],
};
function vecToDir(v: Vec): DirName {
  const r = v.map(c => Math.round(c)) as Vec;
  for (const d of Object.keys(DIR_VEC) as DirName[]) {
    const e = DIR_VEC[d];
    if (e[0] === r[0] && e[1] === r[1] && e[2] === r[2]) return d;
  }
  throw new Error('bad dir ' + v);
}

function rot(v: Vec, axis: 'x' | 'y' | 'z', deg: number): Vec {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  const [x, y, z] = v;
  if (axis === 'x') return [x, y * c - z * s, y * s + z * c];
  if (axis === 'y') return [x * c + z * s, y, -x * s + z * c];
  return [x * c - y * s, x * s + y * c, z];
}

// (face,row,col) -> which cubie (x,y,z in 0..3) and which outward direction.
// Documented convention: row 0 top, col 0 left (looking at the face outside).
function slotToCubie(face: number, row: number, col: number): { x: number; y: number; z: number; dir: DirName } {
  switch (face) {
    case 0: return { x: col, y: 3, z: row, dir: 'PY' };        // U
    case 1: return { x: col, y: 0, z: 3 - row, dir: 'NY' };    // D
    case 2: return { x: col, y: 3 - row, z: 3, dir: 'PZ' };    // F
    case 3: return { x: 3 - col, y: 3 - row, z: 0, dir: 'NZ' };// B
    case 4: return { x: 0, y: 3 - row, z: 3 - col, dir: 'NX' };// L
    default: return { x: 3, y: 3 - row, z: col, dir: 'PX' };   // R
  }
}

const ckey = (x: number, y: number, z: number) => `${x},${y},${z}`;

type Cube = Map<string, Partial<Record<DirName, number>>>;

function stateToCubies(state: CubeState): Cube {
  const cube: Cube = new Map();
  for (let f = 0; f < 6; f++) {
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        const { x, y, z, dir } = slotToCubie(f, row, col);
        const k = ckey(x, y, z);
        if (!cube.has(k)) cube.set(k, {});
        cube.get(k)![dir] = state.stickers[f][row * 4 + col] as unknown as number;
      }
    }
  }
  return cube;
}

function cubiesToState(cube: Cube): number[][] {
  const out: number[][] = Array.from({ length: 6 }, () => new Array(16).fill(-1));
  for (let f = 0; f < 6; f++) {
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        const { x, y, z, dir } = slotToCubie(f, row, col);
        out[f][row * 4 + col] = cube.get(ckey(x, y, z))![dir]!;
      }
    }
  }
  return out;
}

// Physically rotate one slab once (CW per the engine's sign convention).
function rotateSlab(cube: Cube, axis: 'x' | 'y' | 'z', deg: number, layers: number[]): Cube {
  const next: Cube = new Map();
  const axisCoord = (x: number, y: number, z: number) => (axis === 'x' ? x : axis === 'y' ? y : z);
  for (const [k, stickers] of cube) {
    const [x, y, z] = k.split(',').map(Number);
    if (!layers.includes(axisCoord(x, y, z))) {
      next.set(k, { ...stickers });
      continue;
    }
    const c = rot([x - 1.5, y - 1.5, z - 1.5], axis, deg);
    const nk = ckey(Math.round(c[0] + 1.5), Math.round(c[1] + 1.5), Math.round(c[2] + 1.5));
    const moved: Partial<Record<DirName, number>> = next.get(nk) ?? {};
    for (const d of Object.keys(stickers) as DirName[]) {
      moved[vecToDir(rot(DIR_VEC[d], axis, deg))] = stickers[d]!;
    }
    next.set(nk, moved);
  }
  return next;
}

function physicalApply(state: CubeState, move: MoveCode): number[][] {
  const base = move.replace(/['2]/, '');
  const suffix = move.slice(base.length);
  const wide = base.endsWith('w');
  const info = TURN_INFO[base[0]];
  const layers = wide ? info.wide : info.outer;
  const times = suffix === "'" ? 3 : suffix === '2' ? 2 : 1;
  let cube = stateToCubies(state);
  for (let t = 0; t < times; t++) cube = rotateSlab(cube, info.axis, info.sign * 90, layers);
  return cubiesToState(cube);
}

// Build a cube where every sticker has a unique id so we can track each one.
function uniqueState(): CubeState {
  const s = new CubeState();
  for (let f = 0; f < 6; f++) for (let i = 0; i < 16; i++) s.stickers[f][i] = (f * 16 + i) as never;
  return s;
}

// Which (face,index) slots are physically touched by a move (their cubie is in a moving layer).
function movedSlots(move: MoveCode): Set<number> {
  const base = move.replace(/['2]/, '');
  const info = TURN_INFO[base[0]];
  const layers = base.endsWith('w') ? info.wide : info.outer;
  const axisCoord = (c: { x: number; y: number; z: number }) =>
    info.axis === 'x' ? c.x : info.axis === 'y' ? c.y : c.z;
  const set = new Set<number>();
  for (let f = 0; f < 6; f++) for (let i = 0; i < 16; i++) {
    if (layers.includes(axisCoord(slotToCubie(f, (i / 4) | 0, i % 4)))) set.add(f * 16 + i);
  }
  return set;
}

const ALL_BASE = ['U', 'D', 'F', 'B', 'L', 'R', 'Uw', 'Dw', 'Fw', 'Bw', 'Lw', 'Rw'];
const ALL_TEST_MOVES: MoveCode[] = ALL_BASE.flatMap(b => [b, b + "'", b + '2'] as MoveCode[]);

describe('move correctness (vs independent physical cubie model)', () => {
  for (const m of ALL_TEST_MOVES) {
    it(`${m}: every sticker lands in the correct place`, () => {
      const engine = applyMove(uniqueState(), m).stickers as unknown as number[][];
      const physical = physicalApply(uniqueState(), m);
      expect(engine).toEqual(physical);
    });
  }

  for (const m of ALL_TEST_MOVES) {
    it(`${m}: stickers outside the turned layer are not changed`, () => {
      const before = uniqueState();
      const after = applyMove(before, m).stickers as unknown as number[][];
      const moved = movedSlots(m);
      for (let f = 0; f < 6; f++) for (let i = 0; i < 16; i++) {
        if (!moved.has(f * 16 + i)) {
          expect(after[f][i]).toBe(before.stickers[f][i] as unknown as number);
        }
      }
    });
  }

  it('moves are exact bijections (no sticker lost or duplicated)', () => {
    for (const m of ALL_TEST_MOVES) {
      const after = applyMove(uniqueState(), m).stickers as unknown as number[][];
      const seen = new Set(after.flat());
      expect(seen.size).toBe(96);
    }
  });
});
