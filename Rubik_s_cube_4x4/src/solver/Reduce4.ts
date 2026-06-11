import { CubeState } from '../cube/State.js';
import { MoveCode, applyMoves } from '../cube/Moves.js';

// 4x4 reduction: solve centres, then pair edges, then (in Solver) treat the
// cube as a 3x3. Parity fixes handle the two cases unique to even cubes.

function invMove(m: MoveCode): MoveCode {
  return (m.endsWith('2') ? m : m.endsWith("'") ? m.slice(0, -1) : m + "'") as MoveCode;
}
const invSeq = (s: MoveCode[]) => s.slice().reverse().map(invMove);

type Holder = { cube: CubeState; moves: MoveCode[] };
function tryPool(h: Holder, pool: MoveCode[][], ok: (c: CubeState) => boolean, keep: (c: CubeState) => boolean): boolean {
  for (const seq of pool) {
    const c = applyMoves(h.cube, seq);
    if (ok(c) && keep(c)) { h.cube = c; h.moves.push(...seq); return true; }
  }
  return false;
}

// ============================ CENTRES ============================
// Inner slices (a wide turn with the outer layer undone) are the only moves
// that relocate centre pieces between faces.
const SLICES: { seq: MoveCode[]; base: string }[] = [
  { seq: ['Rw', "R'"], base: 'r' }, { seq: ['R', "Rw'"], base: 'r' },
  { seq: ['Lw', "L'"], base: 'l' }, { seq: ['L', "Lw'"], base: 'l' },
  { seq: ['Uw', "U'"], base: 'u' }, { seq: ['U', "Uw'"], base: 'u' },
  { seq: ['Dw', "D'"], base: 'd' }, { seq: ['D', "Dw'"], base: 'd' },
  { seq: ['Fw', "F'"], base: 'f' }, { seq: ['F', "Fw'"], base: 'f' },
  { seq: ['Bw', "B'"], base: 'b' }, { seq: ['B', "Bw'"], base: 'b' },
];
const OUTER_ATOMS: { seq: MoveCode[]; base: string }[] =
  (['U', 'D', 'F', 'B', 'L', 'R'] as const).flatMap(f =>
    ([f, f + "'", f + '2'] as MoveCode[]).map(m => ({ seq: [m], base: f.toLowerCase() })));
const ATOMS = [...SLICES, ...OUTER_ATOMS];

function seqsUpTo(len: number): MoveCode[][] {
  const out: MoveCode[][] = [];
  let frontier: { seq: MoveCode[]; last: string }[] = [{ seq: [], last: '' }];
  for (let l = 0; l < len; l++) {
    const next: typeof frontier = [];
    for (const fr of frontier) for (const a of ATOMS) {
      if (a.base === fr.last) continue;
      const seq = [...fr.seq, ...a.seq];
      out.push(seq); next.push({ seq, last: a.base });
    }
    frontier = next;
  }
  return out;
}

const CENTER_IDX = [5, 6, 9, 10];
const centerMatched = (c: CubeState, face: number) => CENTER_IDX.filter(i => c.stickers[face][i] === face).length;
function changedCenterFaces(seq: MoveCode[]): Set<number> {
  const c = applyMoves(new CubeState(), seq);
  const faces = new Set<number>();
  for (let f = 0; f < 6; f++) for (const i of CENTER_IDX) if (c.stickers[f][i] !== f) faces.add(f);
  return faces;
}
const centerChanges = (seq: MoveCode[]) => {
  const c = applyMoves(new CubeState(), seq); let n = 0;
  for (let f = 0; f < 6; f++) for (const i of CENTER_IDX) if (c.stickers[f][i] !== f) n++;
  return n;
};

// Clean centre 3-cycles (exactly 3 pieces moved), conjugated to reach many triples.
let CENTER_3CYCLES: MoveCode[][] | null = null;
function center3Cycles(): MoveCode[][] {
  if (CENTER_3CYCLES) return CENTER_3CYCLES;
  const seen = new Set<string>();
  const base: MoveCode[][] = [];
  for (const s of SLICES) for (const q of seqsUpTo(2)) {
    const c = [...s.seq, ...q, ...invSeq(s.seq), ...invSeq(q)];
    if (centerChanges(c) !== 3) continue;
    const k = c.join(' '); if (!seen.has(k)) { seen.add(k); base.push(c); }
  }
  const out: MoveCode[][] = [...base];
  const add = (seq: MoveCode[]) => { const k = seq.join(' '); if (!seen.has(k) && centerChanges(seq) === 3) { seen.add(k); out.push(seq); } };
  for (const su of seqsUpTo(1)) for (const c of base) add([...su, ...c, ...invSeq(su)]);
  CENTER_3CYCLES = out;
  return out;
}

// Generators that permute ONLY the centres of faces B(3) and R(5) (adjacent),
// each tagged with how it permutes those 8 positions. Used to BFS the last two
// centres to completion (only C(8,4)=70 arrangements).
const BR_POS = ([3, 5] as const).flatMap(f => CENTER_IDX.map(i => ({ f, i })));
let BR_GENS: { srcOf: number[] }[] | null = null;
function brGenerators(): { srcOf: number[] }[] {
  if (BR_GENS) return BR_GENS;
  const want = new Set([3, 5]);
  const seenPerm = new Set<string>();
  const gens: { srcOf: number[] }[] = [];
  const all = seqsUpTo(2);
  for (const P of SLICES) for (const Q of all) {
    const seq = [...P.seq, ...Q, ...invSeq(P.seq), ...invSeq(Q)];
    const faces = changedCenterFaces(seq);
    if (faces.size === 0 || faces.size > 2) continue;
    if (![...faces].every(f => want.has(f))) continue;
    // permutation of the 8 BR positions
    const labelled = new CubeState();
    BR_POS.forEach((p, k) => { labelled.stickers[p.f][p.i] = k as never; });
    const after = applyMoves(labelled, seq);
    const srcOf = BR_POS.map(p => after.stickers[p.f][p.i] as number);
    const key = srcOf.join(',');
    if (key === '0,1,2,3,4,5,6,7' || seenPerm.has(key)) continue;
    seenPerm.add(key);
    gens.push({ srcOf });
    (gens[gens.length - 1] as { seq?: MoveCode[] }).seq = seq;
  }
  BR_GENS = gens;
  return gens;
}

// BFS the last two centres (B,R) to solved using the BR generators.
function solveLastTwoCenters(h: Holder): void {
  const gens = brGenerators() as { srcOf: number[]; seq: MoveCode[] }[];
  const read = () => BR_POS.map(p => h.cube.stickers[p.f][p.i] as number).join(',');
  const goal = BR_POS.map(p => p.f).join(',');
  const start = read();
  if (start === goal) return;
  const prev = new Map<string, { from: string; gi: number }>();
  prev.set(start, { from: '', gi: -1 });
  const queue = [start];
  let found = false;
  while (queue.length && !found) {
    const cur = queue.shift()!;
    const conf = cur.split(',').map(Number);
    for (let gi = 0; gi < gens.length; gi++) {
      const next = gens[gi].srcOf.map(s => conf[s]).join(',');
      if (prev.has(next)) continue;
      prev.set(next, { from: cur, gi });
      if (next === goal) { found = true; break; }
      queue.push(next);
    }
  }
  if (!found) return;
  const path: number[] = [];
  let s = goal;
  while (prev.get(s)!.gi >= 0) { const p = prev.get(s)!; path.push(p.gi); s = p.from; }
  path.reverse();
  for (const gi of path) { h.cube = applyMoves(h.cube, gens[gi].seq); h.moves.push(...gens[gi].seq); }
}

export function reduceCenters(state: CubeState): MoveCode[] {
  const h: Holder = { cube: state.clone(), moves: [] };
  const comms = center3Cycles();
  // Solve four faces (U,D,F,L) so the last two (B,R) are adjacent.
  const order = [0, 1, 2, 4];
  for (let oi = 0; oi < order.length; oi++) {
    const T = order[oi];
    const locked = order.slice(0, oi);
    const keep = (c: CubeState) => locked.every(f => centerMatched(c, f) === 4);
    for (let guard = 0; guard < 30; guard++) {
      if (centerMatched(h.cube, T) === 4 && keep(h.cube)) break;
      const cur = centerMatched(h.cube, T);
      if (!tryPool(h, comms, c => centerMatched(c, T) > cur, keep)) break;
    }
  }
  solveLastTwoCenters(h);
  return h.moves;
}

// ============================ EDGES ============================
// Standard slice-flip pairing: position two matching wings at front-left and
// front-right, then a fixed merge algorithm pairs them. We keep the merge algs
// fixed and search a short setup that aligns a matching pair (verified to raise
// the paired count while keeping centres solved). The last two edges use the
// dedicated algorithm.
const EDGE_IDX = [1, 2, 4, 7, 8, 11, 13, 14];
function edgeCubieKey(face: number, idx: number): string {
  const r = (idx / 4) | 0, c = idx % 4;
  let x: number, y: number, z: number;
  switch (face) {
    case 0: x = c; y = 3; z = r; break;
    case 1: x = c; y = 0; z = 3 - r; break;
    case 2: x = c; y = 3 - r; z = 3; break;
    case 3: x = 3 - c; y = 3 - r; z = 0; break;
    case 4: x = 0; y = 3 - r; z = 3 - c; break;
    default: x = 3; y = 3 - r; z = c; break;
  }
  return `${x},${y},${z}`;
}
interface Wing { fa: number; ia: number; fb: number; ib: number; }
const DEDGES: [Wing, Wing][] = (() => {
  const byCubie = new Map<string, { face: number; idx: number }[]>();
  for (let f = 0; f < 6; f++) for (const i of EDGE_IDX) {
    const k = edgeCubieKey(f, i);
    if (!byCubie.has(k)) byCubie.set(k, []);
    byCubie.get(k)!.push({ face: f, idx: i });
  }
  const wings: Wing[] = [...byCubie.values()].map(g => ({ fa: g[0].face, ia: g[0].idx, fb: g[1].face, ib: g[1].idx }));
  const byPair = new Map<string, Wing[]>();
  for (const w of wings) {
    const k = [w.fa, w.fb].sort((a, b) => a - b).join();
    if (!byPair.has(k)) byPair.set(k, []);
    byPair.get(k)!.push(w);
  }
  return [...byPair.values()].map(ws => [ws[0], ws[1]] as [Wing, Wing]);
})();
function pairedCount(c: CubeState): number {
  let n = 0;
  for (const [w1, w2] of DEDGES) {
    const a1 = c.stickers[w1.fa][w1.ia], b1 = c.stickers[w1.fb][w1.ib];
    let a2: number, b2: number;
    if (w2.fa === w1.fa) { a2 = c.stickers[w2.fa][w2.ia]; b2 = c.stickers[w2.fb][w2.ib]; }
    else { a2 = c.stickers[w2.fb][w2.ib]; b2 = c.stickers[w2.fa][w2.ia]; }
    if (a1 === a2 && b1 === b2) n++;
  }
  return n;
}
const centersOk = (c: CubeState) => {
  for (let f = 0; f < 6; f++) for (const i of CENTER_IDX) if (c.stickers[f][i] !== f) return false;
  return true;
};

const MERGE_ALGS: MoveCode[][] = [
  ['Uw', "L'", "U'", 'L', "Uw'"],
  ["Uw'", 'R', 'U', "R'", 'Uw'],
  ['Dw', 'R', "F'", 'U', "R'", 'F', "Dw'"], // last two edges
  ['R', "U'", "B'", 'R2'],
];
const SETUP_CACHE = new Map<number, MoveCode[][]>();
function pairSetups(maxLen: number): MoveCode[][] {
  if (SETUP_CACHE.has(maxLen)) return SETUP_CACHE.get(maxLen)!;
  const atoms = ['U', 'D', 'F', 'B', 'L', 'R', 'Uw', 'Dw', 'Fw', 'Bw', 'Lw', 'Rw']
    .flatMap(b => [b, b + "'", b + '2'] as MoveCode[]);
  const out: MoveCode[][] = [[]];
  let frontier: MoveCode[][] = [[]];
  for (let l = 0; l < maxLen; l++) {
    const next: MoveCode[][] = [];
    for (const s of frontier) for (const a of atoms) {
      if (s.length && a[0] === s[s.length - 1][0]) continue;
      const q = [...s, a]; out.push(q); next.push(q);
    }
    frontier = next;
  }
  SETUP_CACHE.set(maxLen, out);
  return out;
}

function pairOnce(h: Holder, setups: MoveCode[][], base: number): boolean {
  for (const s of setups) {
    for (const M of MERGE_ALGS) {
      const c = applyMoves(h.cube, [...s, ...M]);
      if (pairedCount(c) > base && centersOk(c)) {
        h.cube = c; h.moves.push(...s, ...M); return true;
      }
    }
  }
  return false;
}

export function reduceEdges(state: CubeState): MoveCode[] {
  const h: Holder = { cube: state.clone(), moves: [] };
  for (let guard = 0; guard < 20; guard++) {
    const base = pairedCount(h.cube);
    if (base === 12) break;
    // short setups first; fall back to longer ones if a step gets stuck
    if (!pairOnce(h, pairSetups(3), base) && !pairOnce(h, pairSetups(4), base)) break;
  }
  return h.moves;
}
