import type { Player, Point } from './goEngine';

export interface SgfGameInfo {
  boardSize: number;
  rules: 'Chinese' | 'Japanese';
  komi: number;
  blackPlayerName: string;
  whitePlayerName: string;
  handicapStones: Point[];
  moves: { player: Player; x: number; y: number; isPass: boolean }[];
}

// Convert 0-indexed row/col to SGF coordinate letters (a-s)
export function pointToSgfCoords(x: number, y: number): string {
  // SGF coordinates: a=0, b=1, c=2, ... z=25
  const colChar = String.fromCharCode(97 + y);
  const rowChar = String.fromCharCode(97 + x);
  return `${colChar}${rowChar}`;
}

// Convert SGF coordinate letters (a-s) to 0-indexed row/col
export function sgfCoordsToPoint(coords: string): Point | null {
  if (coords.length !== 2) return null;
  const y = coords.charCodeAt(0) - 97;
  const x = coords.charCodeAt(1) - 97;
  return { x, y };
}

// Serialize game history to SGF string
export function exportToSgf(info: SgfGameInfo): string {
  let sgf = '(;';
  
  // Game Header Info
  sgf += `FF[4]GM[1]`; // File Format 4, Game 1 (Go)
  sgf += `SZ[${info.boardSize}]`;
  sgf += `KM[${info.komi}]`;
  sgf += `RU[${info.rules === 'Chinese' ? 'Chinese' : 'Japanese'}]`;
  sgf += `PB[${info.blackPlayerName.replace(/[\]\\()]/g, '')}]`;
  sgf += `PW[${info.whitePlayerName.replace(/[\]\\()]/g, '')}]`;

  // Add Handicap stones if any
  if (info.handicapStones.length > 0) {
    sgf += 'AB';
    for (const p of info.handicapStones) {
      sgf += `[${pointToSgfCoords(p.x, p.y)}]`;
    }
  }

  // Add Moves
  for (const move of info.moves) {
    const coordStr = move.isPass ? '' : pointToSgfCoords(move.x, move.y);
    sgf += `;${move.player}[${coordStr}]`;
  }

  sgf += ')';
  return sgf;
}

// Parse SGF string
export function importFromSgf(sgf: string): SgfGameInfo {
  // Strip comments, white spaces, newlines, and split by semicolons
  const cleanSgf = sgf.trim();
  
  // Basic properties extractors
  const getProp = (prop: string, defaultVal: string): string => {
    const regex = new RegExp(`${prop}\\[([^\\]]*)\\]`);
    const match = cleanSgf.match(regex);
    return match ? match[1] : defaultVal;
  };

  const boardSize = parseInt(getProp('SZ', '19'), 10);
  const rules = getProp('RU', 'Chinese').toLowerCase().includes('jap') ? 'Japanese' : 'Chinese';
  const komi = parseFloat(getProp('KM', '7.5'));
  const blackPlayerName = getProp('PB', 'Black');
  const whitePlayerName = getProp('PW', 'White');

  // Parse Handicap stones (AB[ab][cd]...)
  const handicapStones: Point[] = [];
  const abMatch = cleanSgf.match(/AB(\[[a-z]{2}\])+/);
  if (abMatch) {
    const coordsMatches = abMatch[0].match(/\[[a-z]{2}\]/g);
    if (coordsMatches) {
      for (const m of coordsMatches) {
        const coords = m.slice(1, 3);
        const p = sgfCoordsToPoint(coords);
        if (p && p.x < boardSize && p.y < boardSize) {
          handicapStones.push(p);
        }
      }
    }
  }

  // Parse Moves (;B[ab];W[cd]...)
  const moves: SgfGameInfo['moves'] = [];
  // Regular expression to parse moves
  const moveRegex = /;([BW])\[([a-z]{0,2})\]/g;
  let match;
  while ((match = moveRegex.exec(cleanSgf)) !== null) {
    const player = match[1] as Player;
    const coordStr = match[2];
    
    if (coordStr === '' || coordStr === 'tt' && boardSize < 19) {
      // Pass move
      moves.push({ player, x: -1, y: -1, isPass: true });
    } else {
      const p = sgfCoordsToPoint(coordStr);
      if (p && p.x < boardSize && p.y < boardSize) {
        moves.push({ player, x: p.x, y: p.y, isPass: false });
      } else {
        // Fallback to pass if coordinate string is parsing incorrectly or representing special case
        moves.push({ player, x: -1, y: -1, isPass: true });
      }
    }
  }

  return {
    boardSize,
    rules,
    komi,
    blackPlayerName,
    whitePlayerName,
    handicapStones,
    moves
  };
}
