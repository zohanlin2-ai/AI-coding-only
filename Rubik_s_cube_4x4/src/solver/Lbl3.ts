// Beginner layer-by-layer solver for the 3x3 engine (Cube3), fixed orientation:
// U = white(0) top, D = yellow(1) bottom, F = green(2) front. Uses only face
// turns, so its move codes replay directly onto a reduced 4x4 (outer moves).
//
// Strategy: a curated set of standard algorithms is applied at any slot by
// relabeling face letters under cube-rotation symmetry (sigma) and trying all
// AUF offsets. The engine verifies every candidate, so the solver does not rely
// on getting a particular slot's handedness right and tolerates a generous
// (superset) algorithm list. Piece slots and solved colours come from geometry.

import { Cube3, applyMoves3, Move3 } from './Cube3.js';

// ---- geometry: group facelets into piece slots; solved colour = face index ----
type Facelet = { face: number; idx: number };
function cubieKey(face: number, idx: number): string {
  const r = (idx / 3) | 0, c = idx % 3;
  let x: number, y: number, z: number;
  switch (face) {
    case 0: x = c; y = 2; z = r; break;
    case 1: x = c; y = 0; z = 2 - r; break;
    case 2: x = c; y = 2 - r; z = 2; break;
    case 3: x = 2 - c; y = 2 - r; z = 0; break;
    case 4: x = 0; y = 2 - r; z = 2 - c; break;
    default: x = 2; y = 2 - r; z = c; break;
  }
  return `${x},${y},${z}`;
}
const EDGES: Facelet[][] = [];
const CORNERS: Facelet[][] = [];
{
  const by = new Map<string, Facelet[]>();
  for (let f = 0; f < 6; f++) for (let i = 0; i < 9; i++) {
    if (i === 4) continue;
    const k = cubieKey(f, i);
    if (!by.has(k)) by.set(k, []);
    by.get(k)!.push({ face: f, idx: i });
  }
  for (const g of by.values()) (g.length === 2 ? EDGES : CORNERS).push(g);
}
const edgeFaces = (faces: number[]) => EDGES.find(p => sameSet(p, faces))!;
const cornerFaces = (faces: number[]) => CORNERS.find(p => sameSet(p, faces))!;
const sameSet = (p: Facelet[], faces: number[]) => p.map(s => s.face).sort().join() === [...faces].sort().join();

const col = (c: Cube3, f: number, i: number) => c.stickers[f * 9 + i];
const solvedAt = (c: Cube3, piece: Facelet[]) => piece.every(s => col(c, s.face, s.idx) === s.face);
// current location of the piece whose colour-set equals `faces`
function currentPiece(c: Cube3, list: Facelet[][], faces: number[]): Facelet[] {
  const want = [...faces].sort().join();
  return list.find(p => p.map(s => col(c, s.face, s.idx)).sort().join() === want)!;
}
const onTop = (piece: Facelet[]) => piece.some(s => s.face === 0);

// ---- cube-rotation relabeling (sigma cycles the four side faces) ----
const SIGMA: Record<string, string> = { U: 'U', D: 'D', F: 'R', R: 'B', B: 'L', L: 'F' };
function relabel(seq: string, k: number): string {
  return seq.split(/\s+/).filter(Boolean).map(tok => {
    let f = tok[0];
    for (let i = 0; i < k; i++) f = SIGMA[f];
    return f + tok.slice(1);
  }).join(' ');
}
const parse = (s: string) => s.split(/\s+/).filter(Boolean) as Move3[];
const AUF = ['', 'U', 'U2', "U'"];
// all rotation x AUF variants of an algorithm list, shortest first
function variants(algs: string[]): Move3[][] {
  const res: Move3[][] = [];
  for (const auf of AUF) res.push(parse(auf));        // pure AUF
  for (const a of algs) for (let k = 0; k < 4; k++) for (const auf of AUF)
    res.push(parse((auf ? auf + ' ' : '') + relabel(a, k)));
  return res;
}

type Holder = { cube: Cube3; moves: Move3[] };
function apply(h: Holder, seq: Move3[]): void { h.cube = applyMoves3(h.cube, seq); h.moves.push(...seq); }
function attempt(h: Holder, cands: Move3[][], ok: (c: Cube3) => boolean, keep: (c: Cube3) => boolean): boolean {
  for (const seq of cands) {
    const c = applyMoves3(h.cube, seq);
    if (ok(c) && keep(c)) { apply(h, seq); return true; }
  }
  return false;
}

// place one piece into its slot, preserving `locked`, using algorithm list
function place(h: Holder, slot: Facelet[], faces: number[], list: Facelet[][], locked: Facelet[][], algs: string[]): void {
  const cands = variants(algs);
  const keep = (c: Cube3) => locked.every(p => solvedAt(c, p));
  for (let guard = 0; guard < 10; guard++) {
    if (solvedAt(h.cube, slot) && keep(h.cube)) return;
    if (attempt(h, cands, c => solvedAt(c, slot), keep)) continue;
    // not directly solvable: extract the piece to the top, then retry
    if (attempt(h, cands, c => onTop(currentPiece(c, list, faces)), keep)) continue;
    if (!attempt(h, AUF.slice(1).map(parse), () => true, keep)) return;
  }
}

const SIDES = [2, 5, 3, 4];
const PAIRS: [number, number][] = [[2, 5], [5, 3], [3, 4], [4, 2]];

const CROSS_ALGS = ['F2', "F' U' R U", "U R' F R", "F U' R U R' F'", "U2 F2", "R U R' F2"];
const CORNER_ALGS = ["R U R'", "R U' R'", "R U2 R'", "F' U F", "F' U' F", "F' U2 F",
  "R U2 R' U' R U R'", "R U' R' U R U' R'", "F' U2 F U F' U' F", "R U R' U R U2 R'"];
const EDGE_ALGS = ["U R U' R' U' F' U F", "U' L' U L U F U' F'",
  "U' F' U F U R U' R'", "U L U' L' U' F' U F", "F' U' F U R U R'"];

export function solve3(start: Cube3): Move3[] {
  const h: Holder = { cube: start.clone(), moves: [] };

  // 1. D cross
  const crossSlots = SIDES.map(S => edgeFaces([1, S]));
  crossSlots.forEach((slot, i) => place(h, slot, [1, SIDES[i]], EDGES, crossSlots.slice(0, i), CROSS_ALGS));

  // 2. first-layer corners
  const cornerSlots = PAIRS.map(([a, b]) => cornerFaces([1, a, b]));
  cornerSlots.forEach((slot, i) =>
    place(h, slot, [1, PAIRS[i][0], PAIRS[i][1]], CORNERS, [...crossSlots, ...cornerSlots.slice(0, i)], CORNER_ALGS));

  // 3. middle-layer edges
  const midSlots = PAIRS.map(([a, b]) => edgeFaces([a, b]));
  const firstLayer = [...crossSlots, ...cornerSlots];
  midSlots.forEach((slot, i) =>
    place(h, slot, PAIRS[i], EDGES, [...firstLayer, ...midSlots.slice(0, i)], EDGE_ALGS));

  // 4. last layer
  lastLayer(h, [...firstLayer, ...midSlots]);
  return h.moves;
}
// All AUF-interleaved sequences applying `alg` 0..maxK times (shortest first).
function interleave(alg: string, maxK: number): Move3[][] {
  let frontier: Move3[][] = AUF.map(a => parse(a));
  const out: Move3[][] = [...frontier];
  for (let k = 0; k < maxK; k++) {
    const nf: Move3[][] = [];
    for (const s of frontier) for (const a of AUF) {
      const seq = [...s, ...parse(alg), ...parse(a)];
      nf.push(seq); out.push(seq);
    }
    frontier = nf;
  }
  return out;
}

const PLL = [
  "R U' R U R U R U' R' U' R2",            // U-perm
  "R2 U R U R' U' R' U' R' U R'",          // U-perm
  "R U R' U' R' F R2 U' R' U' R U R' F'",  // T-perm
  "R' F R' B2 R F' R' B2 R2",              // A-perm
  "F R U' R' U' R U R' F' R U R' U' R' F R F'", // Y-perm
];

function lastLayer(h: Holder, locked: Facelet[][]): void {
  const keep = (c: Cube3) => locked.every(p => solvedAt(c, p));
  const llEdges = EDGES.filter(e => e.some(s => s.face === 0));
  const crossOk = (c: Cube3) => llEdges.every(e => col(c, 0, e.find(s => s.face === 0)!.idx) === 0);
  const ollOk = (c: Cube3) => [0, 1, 2, 3, 5, 6, 7, 8].every(i => col(c, 0, i) === 0);

  // OLL edges -> top cross
  attempt(h, interleave("F R U R' U' F'", 3), crossOk, keep);
  // OLL corners -> all of U oriented
  attempt(h, interleave("R U R' U R U2 R'", 4), ollOk, c => crossOk(c) && keep(c));

  // PLL -> solved, using one or (if needed) two algorithms plus AUF.
  const single = AUF.flatMap(a0 => PLL.flatMap(p => AUF.map(a1 => parse(`${a0} ${p} ${a1}`))))
    .concat(AUF.map(parse));
  if (attempt(h, single, c => c.isSolved(), () => true)) return;
  for (const s1 of single) {
    const c1 = applyMoves3(h.cube, s1);
    if (!ollOk(c1) || !keep(c1)) continue;
    for (const s2 of single) {
      if (applyMoves3(c1, s2).isSolved()) { apply(h, s1); apply(h, s2); return; }
    }
  }
}
