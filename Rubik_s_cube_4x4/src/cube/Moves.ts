import { CubeState, Color } from './State.js';

// Rotate a face array 90° clockwise in-place
function rotateFaceCW(face: Color[]): Color[] {
  const f = face;
  return [
    f[12], f[8],  f[4],  f[0],
    f[13], f[9],  f[5],  f[1],
    f[14], f[10], f[6],  f[2],
    f[15], f[11], f[7],  f[3],
  ];
}


// Cycle 4 arrays of indices: a[ai] -> b[bi] -> c[ci] -> d[di] -> a[ai]
function cycle4(
  s: Color[][],
  [a, ai]: [number, number[]],
  [b, bi]: [number, number[]],
  [c, ci]: [number, number[]],
  [d, di]: [number, number[]]
): void {
  const tmp = ai.map(i => s[a][i]);
  ai.forEach((i, k) => { s[a][i] = s[d][di[k]]; });
  di.forEach((i, k) => { s[d][i] = s[c][ci[k]]; });
  ci.forEach((i, k) => { s[c][i] = s[b][bi[k]]; });
  bi.forEach((i, k) => { s[b][i] = tmp[k]; });
}

// Face indices: U=0 D=1 F=2 B=3 L=4 R=5
// Row r, col c => index r*4+c

function rowIdx(r: number): number[] { return [r*4, r*4+1, r*4+2, r*4+3]; }
function colIdx(c: number): number[] { return [c, c+4, c+8, c+12]; }
function colIdxRev(c: number): number[] { return [c+12, c+8, c+4, c]; }
function rowIdxRev(r: number): number[] { return [r*4+3, r*4+2, r*4+1, r*4]; }

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

// Apply a single layer move (CW). layer=0 is outer, layer=1 is inner.
function applyLayerU(s: Color[][], layer: number): void {
  const r = layer;
  cycle4(s,
    [2, rowIdx(r)], [5, rowIdx(r)], [3, rowIdxRev(3 - r)], [4, rowIdx(r)]
  );
  // F->R->B->L (top rows)
  // Actually correct cycle: U face CW => F row r from L, R, B cycle
  // Standard: U CW: F[r] <- L[r], R[r] <- F[r], B[3-r rev] <- R[r], L[r] <- B[3-r rev]
  // Let's redo properly:
  const tmp = rowIdx(r).map(i => s[2][i]);   // save F row r
  rowIdx(r).forEach((i, k) => { s[2][i] = s[4][rowIdx(r)[k]]; });   // F <- L
  rowIdx(r).forEach((i, k) => { s[4][i] = s[3][rowIdxRev(3-r)[k]]; }); // L <- B(rev)
  rowIdxRev(3-r).forEach((i, k) => { s[3][i] = s[5][rowIdx(r)[k]]; });  // B(rev) <- R
  rowIdx(r).forEach((i, k) => { s[5][i] = tmp[k]; });                    // R <- F(saved)
}

function applyLayerD(s: Color[][], layer: number): void {
  const r = 3 - layer;
  const tmp = rowIdx(r).map(i => s[2][i]);
  rowIdx(r).forEach((i, k) => { s[2][i] = s[5][rowIdx(r)[k]]; });
  rowIdx(r).forEach((i, k) => { s[5][i] = s[3][rowIdxRev(3-r)[k]]; });
  rowIdxRev(3-r).forEach((i, k) => { s[3][i] = s[4][rowIdx(r)[k]]; });
  rowIdx(r).forEach((i, k) => { s[4][i] = tmp[k]; });
}

function applyLayerR(s: Color[][], layer: number): void {
  const c = 3 - layer;
  const tmp = colIdx(c).map(i => s[2][i]);
  colIdx(c).forEach((i, k) => { s[2][i] = s[1][colIdx(c)[k]]; });
  colIdx(c).forEach((i, k) => { s[1][i] = s[3][colIdxRev(3-c)[k]]; });
  colIdxRev(3-c).forEach((i, k) => { s[3][i] = s[0][colIdx(c)[k]]; });
  colIdx(c).forEach((i, k) => { s[0][i] = tmp[k]; });
}

function applyLayerL(s: Color[][], layer: number): void {
  const c = layer;
  const tmp = colIdx(c).map(i => s[2][i]);
  colIdx(c).forEach((i, k) => { s[2][i] = s[0][colIdx(c)[k]]; });
  colIdx(c).forEach((i, k) => { s[0][i] = s[3][colIdxRev(3-c)[k]]; });
  colIdxRev(3-c).forEach((i, k) => { s[3][i] = s[1][colIdx(c)[k]]; });
  colIdx(c).forEach((i, k) => { s[1][i] = tmp[k]; });
}

function applyLayerF(s: Color[][], layer: number): void {
  const r = 3 - layer;
  const c = layer;

  const uRow = rowIdx(r).map(i => s[0][i]);
  const rCol = colIdx(c).map(i => s[5][i]);
  const dRow = rowIdx(3 - r).map(i => s[1][i]);
  const lCol = colIdx(3 - c).map(i => s[4][i]);

  rowIdx(r).forEach((i, k) => { s[0][i] = lCol[k]; });
  colIdx(c).forEach((i, k) => { s[5][i] = uRow[k]; });
  rowIdx(3 - r).forEach((i, k) => { s[1][i] = rCol[3 - k]; });
  colIdx(3 - c).forEach((i, k) => { s[4][i] = dRow[3 - k]; });
}

function applyLayerB(s: Color[][], layer: number): void {
  const idx = layer;
  const uRow = rowIdx(idx).map(i => s[0][i]);
  const rCol = colIdx(3-layer).map(i => s[5][i]);
  const dRow = rowIdx(3-idx).map(i => s[1][i]);
  const lCol = colIdx(layer).map(i => s[4][i]);

  rowIdx(idx).forEach((i, k) => { s[0][i] = rCol[k]; });
  colIdx(3-layer).forEach((i, k) => { s[5][i] = dRow[3-k]; });
  rowIdx(3-idx).forEach((i, k) => { s[1][i] = lCol[k]; });
  colIdx(layer).forEach((i, k) => { s[4][i] = uRow[3-k]; });
}

function cwOnce(state: CubeState, move: string): void {
  const s = state.stickers;
  switch (move) {
    case 'U':  s[0] = rotateFaceCW(s[0]); applyLayerU(s, 0); break;
    case 'D':  s[1] = rotateFaceCW(s[1]); applyLayerD(s, 0); break;
    case 'F':  s[2] = rotateFaceCW(s[2]); applyLayerF(s, 0); break;
    case 'B':  s[3] = rotateFaceCW(s[3]); applyLayerB(s, 0); break;
    case 'L':  s[4] = rotateFaceCW(s[4]); applyLayerL(s, 0); break;
    case 'R':  s[5] = rotateFaceCW(s[5]); applyLayerR(s, 0); break;
    case 'Uw': s[0] = rotateFaceCW(s[0]); applyLayerU(s, 0); applyLayerU(s, 1); break;
    case 'Dw': s[1] = rotateFaceCW(s[1]); applyLayerD(s, 0); applyLayerD(s, 1); break;
    case 'Fw': s[2] = rotateFaceCW(s[2]); applyLayerF(s, 0); applyLayerF(s, 1); break;
    case 'Bw': s[3] = rotateFaceCW(s[3]); applyLayerB(s, 0); applyLayerB(s, 1); break;
    case 'Lw': s[4] = rotateFaceCW(s[4]); applyLayerL(s, 0); applyLayerL(s, 1); break;
    case 'Rw': s[5] = rotateFaceCW(s[5]); applyLayerR(s, 0); applyLayerR(s, 1); break;
  }
}

export function applyMove(state: CubeState, move: MoveCode): CubeState {
  const next = state.clone();
  const base = move.replace(/['2]/, '').replace('w', 'w') as string;
  const suffix = move.slice(base.length);

  if (suffix === "'") {
    cwOnce(next, base); cwOnce(next, base); cwOnce(next, base);
  } else if (suffix === '2') {
    cwOnce(next, base); cwOnce(next, base);
  } else {
    cwOnce(next, base);
  }
  return next;
}

export function applyMoves(state: CubeState, moves: MoveCode[]): CubeState {
  return moves.reduce((s, m) => applyMove(s, m), state);
}

export function scramble(state: CubeState, count = 40): { state: CubeState; moves: MoveCode[] } {
  const moves: MoveCode[] = [];
  let current = state.clone();
  const bases = ['U','D','F','B','L','R','Uw','Dw','Fw','Bw','Lw','Rw'];
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
