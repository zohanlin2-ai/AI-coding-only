export interface Cubie {
  x: number; // -1, 0, 1 (Left = -1, Right = 1)
  y: number; // -1, 0, 1 (Down = -1, Up = 1)
  z: number; // -1, 0, 1 (Back = -1, Front = 1)
  colors: {
    U: string | null;
    D: string | null;
    L: string | null;
    R: string | null;
    F: string | null;
    B: string | null;
  };
}

export type Move = 'U' | "U'" | 'D' | "D'" | 'L' | "L'" | 'R' | "R'" | 'F' | "F'" | 'B' | "B'";

export class RubiksCube {
  cubies: Cubie[];

  constructor() {
    this.cubies = [];
    this.reset();
  }

  reset() {
    this.cubies = [];
    const colorsMap = {
      U: 'white',
      D: 'yellow',
      L: 'orange',
      R: 'red',
      F: 'green',
      B: 'blue'
    };
    for (const x of [-1, 0, 1]) {
      for (const y of [-1, 0, 1]) {
        for (const z of [-1, 0, 1]) {
          this.cubies.push({
            x,
            y,
            z,
            colors: {
              U: y === 1 ? colorsMap.U : null,
              D: y === -1 ? colorsMap.D : null,
              L: x === -1 ? colorsMap.L : null,
              R: x === 1 ? colorsMap.R : null,
              F: z === 1 ? colorsMap.F : null,
              B: z === -1 ? colorsMap.B : null
            }
          });
        }
      }
    }
  }

  isSolved(): boolean {
    const faces: ('U' | 'D' | 'L' | 'R' | 'F' | 'B')[] = ['U', 'D', 'L', 'R', 'F', 'B'];
    for (const face of faces) {
      const faceColors = this.cubies
        .filter(c => {
          if (face === 'U') return c.y === 1;
          if (face === 'D') return c.y === -1;
          if (face === 'L') return c.x === -1;
          if (face === 'R') return c.x === 1;
          if (face === 'F') return c.z === 1;
          if (face === 'B') return c.z === -1;
          return false;
        })
        .map(c => c.colors[face])
        .filter(color => color !== null);

      if (faceColors.length === 0) continue;
      const firstColor = faceColors[0];
      if (!faceColors.every(c => c === firstColor)) {
        return false;
      }
    }
    return true;
  }

  clone(): RubiksCube {
    const next = new RubiksCube();
    next.cubies = this.cubies.map(c => ({
      x: c.x,
      y: c.y,
      z: c.z,
      colors: { ...c.colors }
    }));
    return next;
  }

  move(m: Move) {
    const isPrime = m.endsWith("'");
    const baseMove = isPrime ? m.slice(0, -1) : m;
    const turns = isPrime ? 3 : 1;

    for (let i = 0; i < turns; i++) {
      this.rotateFaceClockwise(baseMove);
    }
  }

  private rotateFaceClockwise(face: string) {
    this.cubies.forEach(c => {
      let shouldRotate = false;
      if (face === 'U' && c.y === 1) shouldRotate = true;
      if (face === 'D' && c.y === -1) shouldRotate = true;
      if (face === 'L' && c.x === -1) shouldRotate = true;
      if (face === 'R' && c.x === 1) shouldRotate = true;
      if (face === 'F' && c.z === 1) shouldRotate = true;
      if (face === 'B' && c.z === -1) shouldRotate = true;

      if (shouldRotate) {
        const { x, y, z, colors } = c;
        const newColors = { ...colors };

        if (face === 'R') {
          c.y = z;
          c.z = -y;
          newColors.B = colors.U;
          newColors.D = colors.B;
          newColors.F = colors.D;
          newColors.U = colors.F;
        } else if (face === 'L') {
          c.y = -z;
          c.z = y;
          newColors.F = colors.U;
          newColors.D = colors.F;
          newColors.B = colors.D;
          newColors.U = colors.B;
        } else if (face === 'U') {
          c.x = -z;
          c.z = x;
          newColors.B = colors.L;
          newColors.R = colors.B;
          newColors.F = colors.R;
          newColors.L = colors.F;
        } else if (face === 'D') {
          c.x = z;
          c.z = -x;
          newColors.F = colors.L;
          newColors.R = colors.F;
          newColors.B = colors.R;
          newColors.L = colors.B;
        } else if (face === 'F') {
          c.x = y;
          c.y = -x;
          newColors.R = colors.U;
          newColors.D = colors.R;
          newColors.L = colors.D;
          newColors.U = colors.L;
        } else if (face === 'B') {
          c.x = -y;
          c.y = x;
          newColors.L = colors.U;
          newColors.D = colors.L;
          newColors.R = colors.D;
          newColors.U = colors.R;
        }
        c.colors = newColors;
      }
    });
  }

  scramble(movesCount = 20): Move[] {
    const possibleMoves: Move[] = ['U', "U'", 'D', "D'", 'L', "L'", 'R', "R'", 'F', "F'", 'B', "B'"];
    const scrambleMoves: Move[] = [];
    for (let i = 0; i < movesCount; i++) {
      const randMove = possibleMoves[Math.floor(Math.random() * possibleMoves.length)];
      scrambleMoves.push(randMove);
      this.move(randMove);
    }
    return scrambleMoves;
  }
}
