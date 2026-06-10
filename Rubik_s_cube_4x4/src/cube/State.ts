// 4x4 cube state: 6 faces × 16 stickers = 96 stickers
// Face order: U=0, D=1, F=2, B=3, L=4, R=5
// Sticker index within face: row-major 0..15 (row 0 top, col 0 left)

export type FaceIndex = 0 | 1 | 2 | 3 | 4 | 5;
export type Color = 0 | 1 | 2 | 3 | 4 | 5; // W Y G B O R

export const FACE_COLORS: Color[] = [0, 1, 2, 3, 4, 5];
export const COLOR_HEX = ['#ffffff', '#ffff00', '#00aa00', '#0055cc', '#ff6600', '#cc0000'];
export const FACE_NAMES = ['U', 'D', 'F', 'B', 'L', 'R'];

export class CubeState {
  // stickers[face][index] = color
  stickers: Color[][];

  constructor() {
    this.stickers = Array.from({ length: 6 }, (_, f) =>
      Array(16).fill(f as Color)
    );
  }

  clone(): CubeState {
    const c = new CubeState();
    c.stickers = this.stickers.map(f => [...f]);
    return c;
  }

  isSolved(): boolean {
    return this.stickers.every(face => face.every(s => s === face[0]));
  }

  // Get sticker at face f, row r (0-3), col c (0-3)
  get(f: number, r: number, c: number): Color {
    return this.stickers[f][r * 4 + c];
  }

  set(f: number, r: number, c: number, color: Color): void {
    this.stickers[f][r * 4 + c] = color;
  }
}
