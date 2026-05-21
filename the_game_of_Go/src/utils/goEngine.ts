export type Player = 'B' | 'W';
export type BoardState = (Player | null)[][];

export interface Point {
  x: number; // row index, 0 to N-1
  y: number; // column index, 0 to N-1
}

// Map column index to standard Go letters (excluding 'I')
export const COLS_LETTER = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T'];

export function indexToLabel(x: number, y: number, boardSize: number): string {
  const colLetter = COLS_LETTER[y] || '?';
  const rowNumber = boardSize - x;
  return `${colLetter}${rowNumber}`;
}

export function labelToIndex(label: string, boardSize: number): Point | null {
  if (label.length < 2) return null;
  const colLetter = label[0].toUpperCase();
  const rowNumber = parseInt(label.slice(1), 10);
  if (isNaN(rowNumber)) return null;

  const y = COLS_LETTER.indexOf(colLetter);
  const x = boardSize - rowNumber;

  if (y === -1 || x < 0 || x >= boardSize) return null;
  return { x, y };
}

export function createEmptyBoard(size: number): BoardState {
  const board: BoardState = [];
  for (let i = 0; i < size; i++) {
    board.push(new Array(size).fill(null));
  }
  return board;
}

export function boardToHash(board: BoardState): string {
  return board.map(row => row.map(cell => cell || '.').join('')).join('');
}

// Get adjacent points on the board
export function getAdjacentPoints(x: number, y: number, size: number): Point[] {
  const adj: Point[] = [];
  if (x > 0) adj.push({ x: x - 1, y });
  if (x < size - 1) adj.push({ x: x + 1, y });
  if (y > 0) adj.push({ x, y: y - 1 });
  if (y < size - 1) adj.push({ x, y: y + 1 });
  return adj;
}

// Find a connected group of stones of the same color
export function findGroup(board: BoardState, startX: number, startY: number): {
  stones: Point[];
  color: Player;
} {
  const size = board.length;
  const color = board[startX][startY];
  if (!color) {
    return { stones: [], color: 'B' }; // Should not happen if called on stone
  }

  const visited = new Set<string>();
  const stones: Point[] = [];
  const queue: Point[] = [{ x: startX, y: startY }];
  visited.add(`${startX},${startY}`);

  while (queue.length > 0) {
    const curr = queue.shift()!;
    stones.push(curr);

    const adj = getAdjacentPoints(curr.x, curr.y, size);
    for (const p of adj) {
      const key = `${p.x},${p.y}`;
      if (!visited.has(key) && board[p.x][p.y] === color) {
        visited.add(key);
        queue.push(p);
      }
    }
  }

  return { stones, color };
}

// Calculate the liberties of a group starting at a stone
export function getGroupLiberties(board: BoardState, startX: number, startY: number): {
  stones: Point[];
  liberties: Point[];
} {
  const size = board.length;
  const { stones } = findGroup(board, startX, startY);
  const libertiesMap = new Map<string, Point>();

  for (const stone of stones) {
    const adj = getAdjacentPoints(stone.x, stone.y, size);
    for (const p of adj) {
      if (board[p.x][p.y] === null) {
        libertiesMap.set(`${p.x},${p.y}`, p);
      }
    }
  }

  return {
    stones,
    liberties: Array.from(libertiesMap.values())
  };
}

// Verify rules: Empty, Suicide, and Ko
export function checkMoveLegality(
  board: BoardState,
  x: number,
  y: number,
  player: Player,
  boardHistory: string[] // List of board hashes
): { legal: boolean; reason?: string } {
  const size = board.length;

  // 1. Check if the space is occupied
  if (board[x][y] !== null) {
    return { legal: false, reason: 'Intersection is already occupied' };
  }

  // Create a copy of the board to simulate the move
  const tempBoard = board.map(row => [...row]);
  tempBoard[x][y] = player;

  // 2. Determine captures
  const opponent: Player = player === 'B' ? 'W' : 'B';
  const capturedStones: Point[] = [];

  const adj = getAdjacentPoints(x, y, size);
  for (const p of adj) {
    if (tempBoard[p.x][p.y] === opponent) {
      const { stones, liberties } = getGroupLiberties(tempBoard, p.x, p.y);
      if (liberties.length === 0) {
        capturedStones.push(...stones);
      }
    }
  }

  // Remove captured opponent stones in simulation
  for (const stone of capturedStones) {
    tempBoard[stone.x][stone.y] = null;
  }

  // 3. Suicide Check (Check if player's own group has liberties)
  const { liberties: ownLiberties } = getGroupLiberties(tempBoard, x, y);
  if (ownLiberties.length === 0) {
    return { legal: false, reason: 'Suicide move is not allowed' };
  }

  // 4. Ko Rule Check (Compare with the immediate previous state of the board)
  if (boardHistory.length > 0) {
    const nextHash = boardToHash(tempBoard);
    // Ko rule prevents recreating the exact state from the immediate prior turn (index -2 in history, or last board of the opponent's previous state)
    // In strict Go, it's typically the state before the opponent's turn.
    const prevTurnStateHash = boardHistory.length >= 2 ? boardHistory[boardHistory.length - 2] : null;

    if (prevTurnStateHash && nextHash === prevTurnStateHash) {
      return { legal: false, reason: 'Move violates the Ko rule' };
    }
  }

  return { legal: true };
}

// Executes a move on the board
export function playMove(
  board: BoardState,
  x: number,
  y: number,
  player: Player,
  boardHistory: string[]
): {
  board: BoardState;
  captured: Point[];
  legal: boolean;
  error?: string;
} {
  const legality = checkMoveLegality(board, x, y, player, boardHistory);
  if (!legality.legal) {
    return { board, captured: [], legal: false, error: legality.reason };
  }

  const size = board.length;
  const newBoard = board.map(row => [...row]);
  newBoard[x][y] = player;

  const opponent: Player = player === 'B' ? 'W' : 'B';
  const captured: Point[] = [];

  const adj = getAdjacentPoints(x, y, size);
  for (const p of adj) {
    if (newBoard[p.x][p.y] === opponent) {
      const { stones, liberties } = getGroupLiberties(newBoard, p.x, p.y);
      if (liberties.length === 0) {
        // Capture group
        for (const stone of stones) {
          if (!captured.some(c => c.x === stone.x && c.y === stone.y)) {
            captured.push(stone);
          }
        }
      }
    }
  }

  // Remove captures
  for (const stone of captured) {
    newBoard[stone.x][stone.y] = null;
  }

  return {
    board: newBoard,
    captured,
    legal: true
  };
}

// Calculates territories with optional dead stones excluded
export function calculateTerritory(
  board: BoardState,
  deadStones: Set<string> // Set of "x,y" strings
): {
  blackTerritory: Set<string>;
  whiteTerritory: Set<string>;
  neutral: Set<string>;
} {
  const size = board.length;
  const visited = new Set<string>();

  const blackTerritory = new Set<string>();
  const whiteTerritory = new Set<string>();
  const neutral = new Set<string>();

  // Determine if a cell contains a live stone
  const getLiveStone = (x: number, y: number): Player | null => {
    const stone = board[x][y];
    if (stone === null) return null;
    if (deadStones.has(`${x},${y}`)) return null;
    return stone;
  };

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const key = `${r},${c}`;
      if (visited.has(key)) continue;

      // Skip live stones, they are not territory
      if (getLiveStone(r, c) !== null) {
        continue;
      }

      // We found an empty/dead intersection. Find its connected region.
      const regionPoints: Point[] = [];
      const regionQueue: Point[] = [{ x: r, y: c }];
      visited.add(key);

      const adjacentStones = new Set<Player>();

      while (regionQueue.length > 0) {
        const curr = regionQueue.shift()!;
        regionPoints.push(curr);

        const adj = getAdjacentPoints(curr.x, curr.y, size);
        for (const p of adj) {
          const adjKey = `${p.x},${p.y}`;
          const liveStone = getLiveStone(p.x, p.y);

          if (liveStone !== null) {
            adjacentStones.add(liveStone);
          } else if (!visited.has(adjKey)) {
            visited.add(adjKey);
            regionQueue.push(p);
          }
        }
      }

      // Classify the territory based on bordering stones
      let targetSet: Set<string> | null = null;
      if (adjacentStones.has('B') && !adjacentStones.has('W')) {
        targetSet = blackTerritory;
      } else if (adjacentStones.has('W') && !adjacentStones.has('B')) {
        targetSet = whiteTerritory;
      } else {
        targetSet = neutral;
      }

      for (const p of regionPoints) {
        targetSet.add(`${p.x},${p.y}`);
      }
    }
  }

  return { blackTerritory, whiteTerritory, neutral };
}

export function calculateScore(
  board: BoardState,
  deadStones: Set<string>,
  rules: 'Chinese' | 'Japanese',
  komi: number,
  capturedBlackCount: number, // Prisoners captured by White
  capturedWhiteCount: number  // Prisoners captured by Black
): {
  blackScore: number;
  whiteScore: number;
  blackStonesCount: number;
  whiteStonesCount: number;
  blackTerritoryCount: number;
  whiteTerritoryCount: number;
} {
  const size = board.length;
  const { blackTerritory, whiteTerritory } = calculateTerritory(board, deadStones);

  let blackStonesCount = 0;
  let whiteStonesCount = 0;

  // Count active live stones on the board
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (deadStones.has(`${r},${c}`)) continue;
      if (board[r][c] === 'B') blackStonesCount++;
      if (board[r][c] === 'W') whiteStonesCount++;
    }
  }

  // Count dead stones as prisoners
  let deadBlackCount = 0;
  let deadWhiteCount = 0;
  deadStones.forEach(key => {
    const [rStr, cStr] = key.split(',');
    const r = parseInt(rStr, 10);
    const c = parseInt(cStr, 10);
    if (board[r][c] === 'B') deadBlackCount++;
    if (board[r][c] === 'W') deadWhiteCount++;
  });

  const blackTerritoryCount = blackTerritory.size;
  const whiteTerritoryCount = whiteTerritory.size;

  let blackScore = 0;
  let whiteScore = 0;

  if (rules === 'Chinese') {
    // Chinese Rules: Area Scoring (子空皆地)
    // Score = Live Stones on Board + Territory
    blackScore = blackStonesCount + blackTerritoryCount;
    whiteScore = whiteStonesCount + whiteTerritoryCount + komi;
  } else {
    // Japanese Rules: Territory Scoring (比目法)
    // Score = Territory - Prisoners (Captures + Dead stones remaining on board)
    const totalBlackPrisoners = capturedBlackCount + deadBlackCount;
    const totalWhitePrisoners = capturedWhiteCount + deadWhiteCount;

    blackScore = blackTerritoryCount - totalBlackPrisoners;
    whiteScore = whiteTerritoryCount - totalWhitePrisoners + komi;
  }

  return {
    blackScore,
    whiteScore,
    blackStonesCount,
    whiteStonesCount,
    blackTerritoryCount,
    whiteTerritoryCount
  };
}
