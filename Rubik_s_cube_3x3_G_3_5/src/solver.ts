import { RubiksCube } from './cubeState';
import type { Move, Cubie } from './cubeState';

// Macros for last layer (D face) solving
const K_MOVE: Move[] = ["F'", "R'", "D'", 'R', 'D', 'F'];
const S_MOVE: Move[] = ['R', 'D', "R'", 'D', 'R', 'D', 'D', "R'"];
const P_MOVE: Move[] = ['R', "F'", 'R', 'B', 'B', "R'", 'F', 'R', 'B', 'B', 'R', 'R'];
const U_PERM: Move[] = ['R', 'R', 'D', 'R', 'D', "R'", "D'", "R'", "D'", "R'", 'D', "R'"];

export function solveCube(cube: RubiksCube): Move[] {
  const workingCube = cube.clone();
  const solution: Move[] = [];

  const applyMoves = (moves: Move[]) => {
    moves.forEach(m => {
      workingCube.move(m);
      solution.push(m);
    });
  };

  // Phase 1: White Cross on U layer (y = 1)
  solveWhiteCross(workingCube, applyMoves);

  // Phase 2: White Corners on U layer (y = 1)
  solveWhiteCorners(workingCube, applyMoves);

  // Phase 3: Middle Layer Edges (y = 0)
  solveMiddleEdges(workingCube, applyMoves);

  // Phase 4: Orient Last Layer (OLL) on D layer (y = -1)
  solveOLL(workingCube, applyMoves);

  // Phase 5: Permute Last Layer (PLL) on D layer (y = -1)
  solvePLL(workingCube, applyMoves);

  // Optimize solution by removing redundant moves (e.g. U U' or D D D D)
  return optimizeMoves(solution);
}

export function solveWhiteCross(cube: RubiksCube, apply: (moves: Move[]) => void) {
  // Target edges for White Cross: White-Green, White-Red, White-Blue, White-Orange
  const targets = [
    { colors: ['white', 'green'], targetX: 0, targetZ: 1, sideFace: 'F' as const, nextFace: 'R' as const },
    { colors: ['white', 'red'], targetX: 1, targetZ: 0, sideFace: 'R' as const, nextFace: 'B' as const },
    { colors: ['white', 'blue'], targetX: 0, targetZ: -1, sideFace: 'B' as const, nextFace: 'L' as const },
    { colors: ['white', 'orange'], targetX: -1, targetZ: 0, sideFace: 'L' as const, nextFace: 'F' as const }
  ];

  for (const target of targets) {
    // 1. Find the target piece
    let piece = findEdgePiece(cube, target.colors[0], target.colors[1]);
    
    // Check if already solved
    if (piece.y === 1 && piece.colors.U === 'white' && piece.x === target.targetX && piece.z === target.targetZ) {
      continue;
    }

    // 2. If in U layer (y = 1), bring it to D layer (y = -1)
    if (piece.y === 1) {
      if (piece.x === 0 && piece.z === 1) apply(['F', 'F']);
      else if (piece.x === 1 && piece.z === 0) apply(['R', 'R']);
      else if (piece.x === 0 && piece.z === -1) apply(['B', 'B']);
      else if (piece.x === -1 && piece.z === 0) apply(['L', 'L']);
    }

    // Refresh piece reference
    piece = findEdgePiece(cube, target.colors[0], target.colors[1]);

    // 3. If in middle layer (y = 0), bring it to D layer (y = -1)
    if (piece.y === 0) {
      if (piece.x === 1 && piece.z === 1) { // F-R edge
        apply(['F', 'D', "F'"]);
      } else if (piece.x === -1 && piece.z === 1) { // F-L edge
        apply(["F'", "D'", 'F']);
      } else if (piece.x === 1 && piece.z === -1) { // B-R edge
        apply(['R', 'D', "R'"]);
      } else if (piece.x === -1 && piece.z === -1) { // B-L edge
        apply(["L'", "D'", 'L']);
      }
    }

    // Refresh piece reference
    piece = findEdgePiece(cube, target.colors[0], target.colors[1]);

    // 4. Now it's in D layer (y = -1). Rotate D until it is under the target position
    while (!(piece.x === target.targetX && piece.z === target.targetZ)) {
      apply(['D']);
      piece = findEdgePiece(cube, target.colors[0], target.colors[1]);
    }

    // 5. Insert it to U layer
    if (piece.colors.D === 'white') {
      // White faces down. Just rotate the side face 180 degrees
      apply([`${target.sideFace}`, `${target.sideFace}`] as Move[]);
    } else {
      // White faces side. Use the clean self-restoring insert sequence: D Next Side' Next'
      const side = target.sideFace;
      const next = target.nextFace;
      apply([
        'D',
        next,
        `${side}'` as Move,
        `${next}'` as Move
      ]);
    }
  }
}

export function solveWhiteCorners(cube: RubiksCube, apply: (moves: Move[]) => void) {
  const targets = [
    { colors: ['white', 'green', 'red'], targetX: 1, targetZ: 1, trigger: ["R'", "D'", 'R', 'D'] as Move[] },
    { colors: ['white', 'green', 'orange'], targetX: -1, targetZ: 1, trigger: ['L', 'D', "L'", "D'"] as Move[] },
    { colors: ['white', 'blue', 'red'], targetX: 1, targetZ: -1, trigger: ['R', 'D', "R'", "D'"] as Move[] },
    { colors: ['white', 'blue', 'orange'], targetX: -1, targetZ: -1, trigger: ["L'", "D'", 'L', 'D'] as Move[] }
  ];

  for (const target of targets) {
    let piece = findCornerPiece(cube, target.colors[0], target.colors[1], target.colors[2]);

    // Check if already solved
    if (piece.y === 1 && piece.colors.U === 'white' && piece.x === target.targetX && piece.z === target.targetZ) {
      continue;
    }

    // 1. If in U layer (y = 1), bring it to D layer (y = -1)
    if (piece.y === 1) {
      if (piece.x === 1 && piece.z === 1) apply(["R'", "D'", 'R', 'D']);
      else if (piece.x === -1 && piece.z === 1) apply(['L', 'D', "L'", "D'"]);
      else if (piece.x === 1 && piece.z === -1) apply(['R', 'D', "R'", "D'"]);
      else if (piece.x === -1 && piece.z === -1) apply(["L'", "D'", 'L', 'D']);
    }

    // Refresh piece reference
    piece = findCornerPiece(cube, target.colors[0], target.colors[1], target.colors[2]);

    // 2. Rotate D until it's directly below the target position
    while (!(piece.x === target.targetX && piece.z === target.targetZ)) {
      apply(['D']);
      piece = findCornerPiece(cube, target.colors[0], target.colors[1], target.colors[2]);
    }

    // 3. Repeatedly apply the trigger until solved (max 5 times)
    let safety = 0;
    while (safety < 6 && !(piece.y === 1 && piece.colors.U === 'white')) {
      apply(target.trigger);
      piece = findCornerPiece(cube, target.colors[0], target.colors[1], target.colors[2]);
      safety++;
    }
  }
}

export function solveMiddleEdges(cube: RubiksCube, apply: (moves: Move[]) => void) {
  const targets = [
    { colors: ['green', 'red'], targetX: 1, targetZ: 1, sideFace: 'F' as const, leftFace: 'L' as const, rightFace: 'R' as const },
    { colors: ['green', 'orange'], targetX: -1, targetZ: 1, sideFace: 'F' as const, leftFace: 'L' as const, rightFace: 'R' as const },
    { colors: ['blue', 'red'], targetX: 1, targetZ: -1, sideFace: 'B' as const, leftFace: 'R' as const, rightFace: 'L' as const },
    { colors: ['blue', 'orange'], targetX: -1, targetZ: -1, sideFace: 'B' as const, leftFace: 'R' as const, rightFace: 'L' as const }
  ];

  for (const target of targets) {
    let piece = findEdgePiece(cube, target.colors[0], target.colors[1]);

    // Check if already solved
    if (piece.y === 0 && piece.x === target.targetX && piece.z === target.targetZ) {
      // Must also verify orientation
      const matched = (piece.x === 1 && piece.z === 1 && piece.colors.F === 'green') ||
                      (piece.x === -1 && piece.z === 1 && piece.colors.F === 'green') ||
                      (piece.x === 1 && piece.z === -1 && piece.colors.B === 'blue') ||
                      (piece.x === -1 && piece.z === -1 && piece.colors.B === 'blue');
      if (matched) continue;
    }

    // 1. If trapped in middle layer, kick it out using a dummy insert
    if (piece.y === 0) {
      applyDummyInsert(piece.x, piece.z, apply);
      piece = findEdgePiece(cube, target.colors[0], target.colors[1]);
    }

    // 2. Now it's in D layer (y = -1). Determine matching side face and target direction
    // Rotate D until the side color of the piece matches the side center
    let sideColor = getPieceSideColor(piece);
    let centerFace = getFaceForColor(sideColor);

    while (true) {
      const currentPos = getEdgePositionOnD(piece);
      if (currentPos === centerFace) {
        break;
      }
      apply(['D']);
      piece = findEdgePiece(cube, target.colors[0], target.colors[1]);
      sideColor = getPieceSideColor(piece);
      centerFace = getFaceForColor(sideColor);
    }

    // 3. Determine if inserting left or right
    const otherColor = target.colors.find(c => c !== sideColor)!;
    const destFace = getFaceForColor(otherColor);
    const direction = getInsertDirection(centerFace, destFace);

    if (direction === 'right') {
      applyRightInsert(centerFace, getNextSideFace(centerFace), apply);
    } else {
      applyLeftInsert(centerFace, getPrevSideFace(centerFace), apply);
    }
  }
}

// OLL BFS
export function solveOLL(cube: RubiksCube, apply: (moves: Move[]) => void) {
  const startState = getOLLStateString(cube);
  const queue: { state: string; path: Move[] }[] = [{ state: startState, path: [] }];
  const visited = new Set<string>([startState]);

  if (isOLLSolved(startState)) {
    return;
  }

  while (queue.length > 0) {
    const { path } = queue.shift()!;

    // Generate next states
    // Allowed OLL moves: D, D', D2, K, S
    const nextMoves: { name: string; moves: Move[] }[] = [
      { name: 'D', moves: ['D'] },
      { name: "D'", moves: ["D'"] },
      { name: 'K', moves: K_MOVE },
      { name: 'S', moves: S_MOVE }
    ];

    for (const opt of nextMoves) {
      const nextCube = simulateState(cube, [...path, ...opt.moves]);
      const nextState = getOLLStateString(nextCube);

      if (isOLLSolved(nextState)) {
        apply([...path, ...opt.moves]);
        return;
      }

      if (!visited.has(nextState)) {
        visited.add(nextState);
        queue.push({ state: nextState, path: [...path, ...opt.moves] });
      }
    }
  }
}

// PLL BFS
export function solvePLL(cube: RubiksCube, apply: (moves: Move[]) => void) {
  const startState = getPLLStateString(cube);
  const queue: { state: string; path: Move[] }[] = [{ state: startState, path: [] }];
  const visited = new Set<string>([startState]);

  if (isPLLSolved(startState)) {
    return;
  }

  while (queue.length > 0) {
    const { path } = queue.shift()!;

    // Allowed PLL moves: D, D', P_MOVE, U_PERM
    const nextMoves: { name: string; moves: Move[] }[] = [
      { name: 'D', moves: ['D'] },
      { name: "D'", moves: ["D'"] },
      { name: 'P', moves: P_MOVE },
      { name: 'U', moves: U_PERM }
    ];

    for (const opt of nextMoves) {
      const nextCube = simulateState(cube, [...path, ...opt.moves]);
      const nextState = getPLLStateString(nextCube);

      if (isPLLSolved(nextState)) {
        apply([...path, ...opt.moves]);
        return;
      }

      if (!visited.has(nextState)) {
        visited.add(nextState);
        queue.push({ state: nextState, path: [...path, ...opt.moves] });
      }
    }
  }
}

// HELPER FUNCTIONS FOR FINDING PIECES
function findEdgePiece(cube: RubiksCube, c1: string, c2: string): Cubie {
  return cube.cubies.find(c => 
    Object.values(c.colors).includes(c1) && 
    Object.values(c.colors).includes(c2) &&
    Object.values(c.colors).filter(x => x !== null).length === 2
  )!;
}

function findCornerPiece(cube: RubiksCube, c1: string, c2: string, c3: string): Cubie {
  return cube.cubies.find(c => 
    Object.values(c.colors).includes(c1) && 
    Object.values(c.colors).includes(c2) && 
    Object.values(c.colors).includes(c3) &&
    Object.values(c.colors).filter(x => x !== null).length === 3
  )!;
}

// HELPER FUNCTIONS FOR MIDDLE LAYER
function applyDummyInsert(x: number, z: number, apply: (moves: Move[]) => void) {
  if (x === 1 && z === 1) applyRightInsert('F', 'R', apply);
  else if (x === -1 && z === 1) applyLeftInsert('F', 'L', apply);
  else if (x === 1 && z === -1) applyLeftInsert('B', 'R', apply);
  else applyRightInsert('B', 'L', apply);
}

function getPieceSideColor(piece: Cubie): string {
  // Return the sticker color that is NOT on D
  const sideKey = Object.keys(piece.colors).find(k => k !== 'D' && piece.colors[k as keyof typeof piece.colors] !== null)!;
  return piece.colors[sideKey as keyof typeof piece.colors]!;
}

function getFaceForColor(color: string): 'F' | 'R' | 'B' | 'L' {
  if (color === 'green') return 'F';
  if (color === 'red') return 'R';
  if (color === 'blue') return 'B';
  return 'L'; // orange
}

function getEdgePositionOnD(piece: Cubie): 'F' | 'R' | 'B' | 'L' {
  if (piece.x === 0 && piece.z === 1) return 'F';
  if (piece.x === 1 && piece.z === 0) return 'R';
  if (piece.x === 0 && piece.z === -1) return 'B';
  return 'L';
}

function getInsertDirection(center: 'F' | 'R' | 'B' | 'L', dest: 'F' | 'R' | 'B' | 'L'): 'left' | 'right' {
  const order = ['F', 'R', 'B', 'L'];
  const cIdx = order.indexOf(center);
  const dIdx = order.indexOf(dest);
  if ((cIdx + 1) % 4 === dIdx) return 'right';
  return 'left';
}

function getNextSideFace(face: 'F' | 'R' | 'B' | 'L'): 'F' | 'R' | 'B' | 'L' {
  const order = ['F', 'R', 'B', 'L'] as const;
  return order[(order.indexOf(face) + 1) % 4];
}

function getPrevSideFace(face: 'F' | 'R' | 'B' | 'L'): 'F' | 'R' | 'B' | 'L' {
  const order = ['F', 'R', 'B', 'L'] as const;
  return order[(order.indexOf(face) + 3) % 4];
}

function applyRightInsert(side: 'F' | 'R' | 'B' | 'L', right: 'F' | 'R' | 'B' | 'L', apply: (moves: Move[]) => void) {
  apply([
    "D'",
    `${right}'` as Move,
    'D',
    right,
    'D',
    side,
    "D'",
    `${side}'` as Move
  ]);
}

function applyLeftInsert(side: 'F' | 'R' | 'B' | 'L', left: 'F' | 'R' | 'B' | 'L', apply: (moves: Move[]) => void) {
  apply([
    'D',
    left,
    "D'",
    `${left}'` as Move,
    "D'",
    `${side}'` as Move,
    'D',
    side
  ]);
}

// OLL STATE HELPERS
function getOLLStateString(cube: RubiksCube): string {
  const coords = [
    [-1, 1], [0, 1], [1, 1],
    [-1, 0],         [1, 0],
    [-1, -1], [0, -1], [1, -1]
  ];
  return coords.map(([x, z]) => {
    const c = cube.cubies.find(cubie => cubie.x === x && cubie.y === -1 && cubie.z === z)!;
    const yellowFace = Object.keys(c.colors).find(k => c.colors[k as keyof typeof c.colors] === 'yellow')!;
    return yellowFace;
  }).join('');
}

function isOLLSolved(state: string): boolean {
  return state === 'DDDDDDDD';
}

// PLL STATE HELPERS
function getPLLStateString(cube: RubiksCube): string {
  const getColorsForFace = (face: 'F' | 'R' | 'B' | 'L', coords: [number, number][]) => {
    return coords.map(([x, z]) => {
      const c = cube.cubies.find(cubie => cubie.x === x && cubie.y === -1 && cubie.z === z)!;
      return c.colors[face] || '';
    }).join('');
  };

  const fStr = getColorsForFace('F', [[-1, 1], [0, 1], [1, 1]]);
  const rStr = getColorsForFace('R', [[1, 1], [1, 0], [1, -1]]);
  const bStr = getColorsForFace('B', [[1, -1], [0, -1], [-1, -1]]);
  const lStr = getColorsForFace('L', [[-1, -1], [-1, 0], [-1, 1]]);

  return `${fStr}|${rStr}|${bStr}|${lStr}`;
}

function isPLLSolved(state: string): boolean {
  return state === 'greengreengreen|redredred|blueblueblue|orangeorangeorange';
}

function simulateState(cube: RubiksCube, path: Move[]): RubiksCube {
  const next = cube.clone();
  path.forEach(m => next.move(m));
  return next;
}

// OPTIMIZE MOVES (Remove redundancies)
function optimizeMoves(moves: Move[]): Move[] {
  let optimized = [...moves];
  let changed = true;

  while (changed) {
    changed = false;
    const next: Move[] = [];
    let i = 0;

    while (i < optimized.length) {
      const m1 = optimized[i];
      const m2 = optimized[i + 1];

      if (m2) {
        // Double cancel (R R' or R' R)
        const isM1Prime = m1.endsWith("'");
        const isM2Prime = m2.endsWith("'");
        const baseM1 = isM1Prime ? m1.slice(0, -1) : m1;
        const baseM2 = isM2Prime ? m2.slice(0, -1) : m2;

        if (baseM1 === baseM2 && isM1Prime !== isM2Prime) {
          i += 2;
          changed = true;
          continue;
        }

        // Standard merge (e.g. D2 D -> D', or D D -> D2, or D D2 -> D', etc.)
        // For simplicity, let's just do standard adjacent cancelations.
      }
      next.push(m1);
      i++;
    }
    optimized = next;
  }
  return optimized;
}
