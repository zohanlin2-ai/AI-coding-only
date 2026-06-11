// A correct, self-contained 3x3 engine built with the same geometric
// permutation technique as the 4x4 engine (collision-free facelet keys).
// The reduced 4x4 is solved by treating it as a 3x3 and replaying the same
// face-turn move codes back onto the 4x4 with outer moves.

export type Move3 =
  | 'U' | "U'" | 'U2' | 'D' | "D'" | 'D2'
  | 'F' | "F'" | 'F2' | 'B' | "B'" | 'B2'
  | 'L' | "L'" | 'L2' | 'R' | "R'" | 'R2';

// Face index: U=0 D=1 F=2 B=3 L=4 R=5. Sticker index: row*3+col, row 0 top.
type Axis = 'x' | 'y' | 'z';
const AXIS_INDEX: Record<Axis, 0 | 1 | 2> = { x: 0, y: 1, z: 2 };
const NORMAL: [number, number, number][] = [
  [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], [-1, 0, 0], [1, 0, 0],
];
// Tangential offset of facelet (row,col), coords centred at 0 in {-1,0,1}.
function tangential(face: number, row: number, col: number): [number, number, number] {
  switch (face) {
    case 0: return [col - 1, 0, row - 1];
    case 1: return [col - 1, 0, 1 - row];
    case 2: return [col - 1, 1 - row, 0];
    case 3: return [1 - col, 1 - row, 0];
    case 4: return [0, 1 - row, 1 - col];
    default: return [0, 1 - row, col - 1];
  }
}
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
const gridOf = (v: number) => Math.round(v + 1);

const KEY_SCALE = 2, CUBIE_SCALE = 1;
const SLOT_BY_KEY = new Map<string, number>();
for (let f = 0; f < 6; f++)
  for (let r = 0; r < 3; r++)
    for (let c = 0; c < 3; c++)
      SLOT_BY_KEY.set(keyOf(facePos(f, r, c, KEY_SCALE)), f * 9 + (r * 3 + c));

interface TurnInfo { axis: Axis; sign: number; layer: number }
const TURN: Record<string, TurnInfo> = {
  U: { axis: 'y', sign: -1, layer: 2 },
  D: { axis: 'y', sign: +1, layer: 0 },
  F: { axis: 'z', sign: -1, layer: 2 },
  B: { axis: 'z', sign: +1, layer: 0 },
  L: { axis: 'x', sign: +1, layer: 0 },
  R: { axis: 'x', sign: -1, layer: 2 },
};

function buildPerm(info: TurnInfo): Int16Array {
  const perm = new Int16Array(54);
  for (let i = 0; i < 54; i++) perm[i] = i;
  const ai = AXIS_INDEX[info.axis];
  for (let f = 0; f < 6; f++)
    for (let r = 0; r < 3; r++)
      for (let c = 0; c < 3; c++) {
        if (gridOf(facePos(f, r, c, CUBIE_SCALE)[ai]) !== info.layer) continue;
        const dest = SLOT_BY_KEY.get(keyOf(rotateVec(facePos(f, r, c, KEY_SCALE), info.axis, info.sign * 90)))!;
        perm[f * 9 + (r * 3 + c)] = dest;
      }
  return perm;
}
const PERM_CW: Record<string, Int16Array> = {};
for (const b of Object.keys(TURN)) PERM_CW[b] = buildPerm(TURN[b]);

export class Cube3 {
  stickers: number[]; // 54, value = face colour 0..5

  constructor(stickers?: number[]) {
    this.stickers = stickers ? stickers.slice() : Array.from({ length: 54 }, (_, i) => (i / 9) | 0);
  }
  clone(): Cube3 { return new Cube3(this.stickers); }
  isSolved(): boolean {
    for (let f = 0; f < 6; f++) for (let i = 1; i < 9; i++) if (this.stickers[f * 9 + i] !== this.stickers[f * 9]) return false;
    return true;
  }
  get(face: number, idx: number): number { return this.stickers[face * 9 + idx]; }
}

export function applyMove3(cube: Cube3, move: Move3): Cube3 {
  const base = move.replace(/['2]/, '');
  const suffix = move.slice(base.length);
  const perm = PERM_CW[base];
  const out = cube.clone();
  const times = suffix === "'" ? 3 : suffix === '2' ? 2 : 1;
  for (let t = 0; t < times; t++) {
    const flat = out.stickers.slice();
    for (let src = 0; src < 54; src++) if (perm[src] !== src) out.stickers[perm[src]] = flat[src];
  }
  return out;
}

export function applyMoves3(cube: Cube3, moves: Move3[]): Cube3 {
  return moves.reduce((c, m) => applyMove3(c, m), cube);
}

const SUF = ['', "'", '2'] as const;
const BASES3 = ['U', 'D', 'F', 'B', 'L', 'R'];
export const ALL_MOVES3: Move3[] = BASES3.flatMap(b => SUF.map(s => (b + s) as Move3));

export function scramble3(n = 30): { cube: Cube3; moves: Move3[] } {
  let cube = new Cube3();
  const moves: Move3[] = [];
  for (let i = 0; i < n; i++) {
    const m = ALL_MOVES3[Math.floor(Math.random() * ALL_MOVES3.length)];
    moves.push(m);
    cube = applyMove3(cube, m);
  }
  return { cube, moves };
}
