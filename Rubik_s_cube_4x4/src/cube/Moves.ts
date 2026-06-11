import { CubeState, Color } from './State.js';

// 4x4 move engine derived directly from cube geometry, so every move is a real
// rigid rotation. This guarantees the moves compose like a physical cube and
// that the 3D renderer (which shares this geometry) animates turns seamlessly.
//
// Face index: U=0 D=1 F=2 B=3 L=4 R=5. Sticker index within a face: row*4+col,
// row 0 = top, col 0 = left (as seen looking at the face from outside).

export type MoveCode =
  | 'U' | "U'" | 'U2'
  | 'D' | "D'" | 'D2'
  | 'F' | "F'" | 'F2'
  | 'B' | "B'" | 'B2'
  | 'L' | "L'" | 'L2'
  | 'R' | "R'" | 'R2'
  | 'Uw' | "Uw'" | 'Uw2'
  | 'Dw' | "Dw'" | 'Dw2'
  | 'Fw' | "Fw'" | 'Fw2'
  | 'Bw' | "Bw'" | 'Bw2'
  | 'Lw' | "Lw'" | 'Lw2'
  | 'Rw' | "Rw'" | 'Rw2';

export const ALL_MOVES: MoveCode[] = [
  'U', "U'", 'U2', 'D', "D'", 'D2',
  'F', "F'", 'F2', 'B', "B'", 'B2',
  'L', "L'", 'L2', 'R', "R'", 'R2',
  'Uw', "Uw'", 'Uw2', 'Dw', "Dw'", 'Dw2',
  'Fw', "Fw'", 'Fw2', 'Bw', "Bw'", 'Bw2',
  'Lw', "Lw'", 'Lw2', 'Rw', "Rw'", 'Rw2',
];

type Axis = 'x' | 'y' | 'z';
const AXIS_INDEX: Record<Axis, 0 | 1 | 2> = { x: 0, y: 1, z: 2 };

// Per-face outward normal and the in-plane (tangential) offset of facelet
// (row,col). row 0 = top, col 0 = left looking at the face from outside.
const NORMAL: [number, number, number][] = [
  [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], [-1, 0, 0], [1, 0, 0], // U D F B L R
];
function tangential(face: number, row: number, col: number): [number, number, number] {
  switch (face) {
    case 0: return [col - 1.5, 0, row - 1.5];          // U
    case 1: return [col - 1.5, 0, 1.5 - row];          // D
    case 2: return [col - 1.5, 1.5 - row, 0];          // F
    case 3: return [1.5 - col, 1.5 - row, 0];          // B
    case 4: return [0, 1.5 - row, 1.5 - col];          // L
    default: return [0, 1.5 - row, col - 1.5];         // R
  }
}

// Facelet position. `scale` sets how far along the normal the point sits.
// scale=2 (> the tangential max of 1.5) is used for the rotation/match key so
// that facelets from two faces meeting at a shared edge stay distinct points.
// scale=1.5 gives the underlying cubie, used for layer membership.
function facePos(face: number, row: number, col: number, scale: number): [number, number, number] {
  const n = NORMAL[face], t = tangential(face, row, col);
  return [n[0] * scale + t[0], n[1] * scale + t[1], n[2] * scale + t[2]];
}

function rotateVec(p: [number, number, number], axis: Axis, deg: number): [number, number, number] {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  const [x, y, z] = p;
  if (axis === 'x') return [x, y * c - z * s, y * s + z * c];
  if (axis === 'y') return [x * c + z * s, y, -x * s + z * c];
  return [x * c - y * s, x * s + y * c, z];
}

const keyOf = (p: [number, number, number]) => p.map(v => Math.round(v * 2) / 2).join(',');
const gridOf = (v: number) => Math.round(v + 1.5);

const KEY_SCALE = 2;   // separates facelets that share a cube edge
const CUBIE_SCALE = 1.5; // collapses a facelet onto its cubie for layer tests

// Slot lookup: facelet key -> linear sticker index (face*16 + row*4 + col).
const SLOT_BY_KEY = new Map<string, number>();
for (let f = 0; f < 6; f++)
  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 4; c++)
      SLOT_BY_KEY.set(keyOf(facePos(f, r, c, KEY_SCALE)), f * 16 + (r * 4 + c));

// Per-base turn geometry. `sign` is the rotation (deg = sign*90) for one
// clockwise turn, chosen so each move matches the conventional cube direction.
// `outer`/`wide` are the cubie layers (0..3 along the axis) that rotate.
export interface TurnInfo { axis: Axis; sign: number; outer: number[]; wide: number[] }
export const TURN_INFO: Record<string, TurnInfo> = {
  U: { axis: 'y', sign: -1, outer: [3], wide: [3, 2] },
  D: { axis: 'y', sign: +1, outer: [0], wide: [0, 1] },
  F: { axis: 'z', sign: -1, outer: [3], wide: [3, 2] },
  B: { axis: 'z', sign: +1, outer: [0], wide: [0, 1] },
  L: { axis: 'x', sign: +1, outer: [0], wide: [0, 1] },
  R: { axis: 'x', sign: -1, outer: [3], wide: [3, 2] },
};

// Build a permutation for one clockwise turn of the given layers:
// perm[src] = dest means the sticker at slot `src` moves to slot `dest`.
function buildPerm(info: TurnInfo, layers: number[]): Int16Array {
  const perm = new Int16Array(96);
  for (let i = 0; i < 96; i++) perm[i] = i;
  const ai = AXIS_INDEX[info.axis];
  for (let f = 0; f < 6; f++) {
    for (let r = 0; r < 4; r++) {
      for (let c = 0; c < 4; c++) {
        // Layer membership uses the cubie position; rotation uses the key point.
        if (!layers.includes(gridOf(facePos(f, r, c, CUBIE_SCALE)[ai]))) continue;
        const rotated = rotateVec(facePos(f, r, c, KEY_SCALE), info.axis, info.sign * 90);
        const dest = SLOT_BY_KEY.get(keyOf(rotated))!;
        perm[f * 16 + (r * 4 + c)] = dest;
      }
    }
  }
  return perm;
}

const PERM_CW: Record<string, { outer: Int16Array; wide: Int16Array }> = {};
for (const base of Object.keys(TURN_INFO)) {
  const info = TURN_INFO[base];
  PERM_CW[base] = { outer: buildPerm(info, info.outer), wide: buildPerm(info, info.wide) };
}

function applyPerm(state: CubeState, perm: Int16Array): void {
  const flat = new Array<Color>(96);
  for (let f = 0; f < 6; f++) for (let i = 0; i < 16; i++) flat[f * 16 + i] = state.stickers[f][i];
  for (let src = 0; src < 96; src++) {
    const dest = perm[src];
    if (dest === src) continue;
    state.stickers[(dest / 16) | 0][dest % 16] = flat[src];
  }
}

export function applyMove(state: CubeState, move: MoveCode): CubeState {
  const next = state.clone();
  const base = move.replace(/['2]/, '');
  const suffix = move.slice(base.length);
  const wide = base.endsWith('w');
  const face = base[0];
  const perm = wide ? PERM_CW[face].wide : PERM_CW[face].outer;

  const times = suffix === "'" ? 3 : suffix === '2' ? 2 : 1;
  for (let t = 0; t < times; t++) applyPerm(next, perm);
  return next;
}

export function applyMoves(state: CubeState, moves: MoveCode[]): CubeState {
  return moves.reduce((s, m) => applyMove(s, m), state);
}

export function scramble(state: CubeState, count = 40): { state: CubeState; moves: MoveCode[] } {
  const moves: MoveCode[] = [];
  let current = state.clone();
  const bases = ['U', 'D', 'F', 'B', 'L', 'R', 'Uw', 'Dw', 'Fw', 'Bw', 'Lw', 'Rw'];
  const suffixes = ['', "'", '2'];
  for (let i = 0; i < count; i++) {
    const b = bases[Math.floor(Math.random() * bases.length)];
    const sx = suffixes[Math.floor(Math.random() * 3)];
    const m = (b + sx) as MoveCode;
    moves.push(m);
    current = applyMove(current, m);
  }
  return { state: current, moves };
}
