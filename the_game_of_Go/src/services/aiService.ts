import { type BoardState, type Player, type Point, getAdjacentPoints, checkMoveLegality, getGroupLiberties, indexToLabel, calculateTerritory, playMove, boardToHash } from '../utils/goEngine';

export interface AiConfig {
  provider: 'local' | 'gemini' | 'groq' | 'openrouter' | 'openai' | 'anthropic' | 'mcts';
  model: string;
  apiKey: string;
  customProxyUrl?: string;
}

// 1. Local Heuristic AI Implementation
export interface HeuristicContext {
  blackTerritory: Set<string>;
  whiteTerritory: Set<string>;
  regionSizeMap: Map<string, number>;
  isEndGame: boolean;
  ownThreshold: number;
  opponentThreshold: number;
}

export function computeHeuristicContext(board: BoardState): HeuristicContext {
  const size = board.length;
  const { blackTerritory, whiteTerritory } = calculateTerritory(board, new Set());

  const visited = new Set<string>();
  const regionSizeMap = new Map<string, number>();
  let totalEmpty = 0;

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (board[r][c] !== null) continue;
      totalEmpty++;
      const key = `${r},${c}`;
      if (visited.has(key)) continue;

      const region: string[] = [];
      const queue: Point[] = [{ x: r, y: c }];
      visited.add(key);

      while (queue.length > 0) {
        const curr = queue.shift()!;
        region.push(`${curr.x},${curr.y}`);

        const adj = getAdjacentPoints(curr.x, curr.y, size);
        for (const p of adj) {
          if (board[p.x][p.y] === null) {
            const adjKey = `${p.x},${p.y}`;
            if (!visited.has(adjKey)) {
              visited.add(adjKey);
              queue.push(p);
            }
          }
        }
      }

      const regionSize = region.length;
      for (const pt of region) {
        regionSizeMap.set(pt, regionSize);
      }
    }
  }

  const isEndGame = totalEmpty < (size * size * 0.35);
  const ownThreshold = size === 9 ? 20 : size === 13 ? 40 : 80;
  const opponentThreshold = size === 9 ? 10 : size === 13 ? 18 : 30;

  return {
    blackTerritory,
    whiteTerritory,
    regionSizeMap,
    isEndGame,
    ownThreshold,
    opponentThreshold
  };
}

export function getMoveHeuristicScore(
  board: BoardState,
  move: Point,
  player: Player,
  _boardHistory: string[],
  context?: HeuristicContext
): number {
  const size = board.length;
  const opponent: Player = player === 'B' ? 'W' : 'B';
  const ctx = context || computeHeuristicContext(board);

  let score = 0;

  // Simulate placing the stone
  const tempBoard = board.map(row => [...row]);
  tempBoard[move.x][move.y] = player;

  // A. Capture Heuristic (High Priority)
  const adj = getAdjacentPoints(move.x, move.y, size);
  let totalCaptured = 0;
  for (const p of adj) {
    if (tempBoard[p.x][p.y] === opponent) {
      const { stones, liberties } = getGroupLiberties(tempBoard, p.x, p.y);
      if (liberties.length === 0) {
        totalCaptured += stones.length;
      }
    }
  }
  score += totalCaptured * 15;

  // If opponent group is in atari, threaten it
  for (const p of adj) {
    if (board[p.x][p.y] === opponent) {
      const { liberties } = getGroupLiberties(board, p.x, p.y);
      if (liberties.length === 2) {
        score += 4;
      }
    }
  }

  // B. Self-Preservation: Check liberties of our new group
  const { liberties: ownLiberties } = getGroupLiberties(tempBoard, move.x, move.y);
  const libertiesCount = ownLiberties.length;
  
  if (libertiesCount === 1) {
    if (totalCaptured === 0) {
      score -= 25;
    }
  } else if (libertiesCount === 2) {
    score += 2;
  } else if (libertiesCount >= 3) {
    score += 5;
  }

  // Saving existing group from Atari
  const originalAdj = getAdjacentPoints(move.x, move.y, size);
  for (const p of originalAdj) {
    if (board[p.x][p.y] === player) {
      const { liberties: originalLiberties } = getGroupLiberties(board, p.x, p.y);
      if (originalLiberties.length === 1) {
        if (libertiesCount > 1) {
          score += 12;
        }
      }
    }
  }

  // C. Positional Heuristics
  const distEdgeX = Math.min(move.x, size - 1 - move.x);
  const distEdgeY = Math.min(move.y, size - 1 - move.y);
  const minEdgeDist = Math.min(distEdgeX, distEdgeY);

  if (minEdgeDist === 2 || minEdgeDist === 3) {
    score += 3;
  } else if (minEdgeDist === 1) {
    score += 1;
  } else if (minEdgeDist === 0) {
    score -= 5;
  }

  // D. Corner and Star points bias in early game
  let totalStones = 0;
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (board[r][c] !== null) totalStones++;
    }
  }
  if (totalStones < size) {
    const isStarPoint = (move.x === 3 || move.x === size - 4 || move.x === Math.floor(size / 2)) &&
                        (move.y === 3 || move.y === size - 4 || move.y === Math.floor(size / 2));
    if (isStarPoint) {
      score += 4;
    }
  }

  // E. Connectivity
  let nearFriendly = false;
  for (const p of originalAdj) {
    if (board[p.x][p.y] === player) {
      nearFriendly = true;
    }
  }
  if (nearFriendly) {
    score += 1.5;
  }

  // G. Territory Heuristics
  const moveKey = `${move.x},${move.y}`;
  const isOwnTerritory = player === 'B' ? ctx.blackTerritory.has(moveKey) : ctx.whiteTerritory.has(moveKey);
  const isOpponentTerritory = player === 'B' ? ctx.whiteTerritory.has(moveKey) : ctx.blackTerritory.has(moveKey);

  const regionSize = ctx.regionSizeMap.get(moveKey) || 0;

  if (isOwnTerritory) {
    if (ctx.isEndGame || regionSize <= ctx.ownThreshold) {
      score -= 50;
    }
  } else if (isOpponentTerritory && totalCaptured === 0) {
    if (ctx.isEndGame || regionSize <= ctx.opponentThreshold) {
      score -= 50;
    }
  }

  return score;
}

// 1. Local Heuristic AI Implementation
export function computeLocalHeuristicMove(
  board: BoardState,
  player: Player,
  boardHistory: string[]
): Point | 'PASS' {
  const size = board.length;
  const legalMoves: Point[] = [];

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (checkMoveLegality(board, r, c, player, boardHistory).legal) {
        legalMoves.push({ x: r, y: c });
      }
    }
  }

  if (legalMoves.length === 0) {
    return 'PASS';
  }

  const context = computeHeuristicContext(board);
  let bestMove: Point = legalMoves[0];
  let bestScore = -Infinity;

  for (const move of legalMoves) {
    let score = getMoveHeuristicScore(board, move, player, boardHistory, context);
    score += Math.random() * 0.8;

    if (score > bestScore) {
      bestScore = score;
      bestMove = move;
    }
  }

  if (bestScore < -20) {
    return 'PASS';
  }

  return bestMove;
}

// 1b. MCTS AI Implementation
export function computeMctsMove(
  board: BoardState,
  player: Player,
  boardHistory: string[],
  iterations?: number
): Point | 'PASS' {
  const size = board.length;
  const iters = iterations || (size === 9 ? 300 : size === 13 ? 150 : 80);
  const opponent: Player = player === 'B' ? 'W' : 'B';

  const legalMoves: (Point | 'PASS')[] = [];
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (checkMoveLegality(board, r, c, player, boardHistory).legal) {
        legalMoves.push({ x: r, y: c });
      }
    }
  }
  legalMoves.push('PASS');

  if (legalMoves.length === 1 && legalMoves[0] === 'PASS') {
    return 'PASS';
  }

  interface MctsNode {
    move: Point | 'PASS';
    player: Player;
    visits: number;
    wins: number;
    parent: MctsNode | null;
    children: MctsNode[];
    untriedMoves: (Point | 'PASS')[];
    boardState: BoardState;
    history: string[];
    heuristicScore: number;
  }

  const root: MctsNode = {
    move: 'PASS',
    player: opponent,
    visits: 0,
    wins: 0,
    parent: null,
    children: [],
    untriedMoves: [...legalMoves],
    boardState: board,
    history: [...boardHistory],
    heuristicScore: 0
  };

  for (let i = 0; i < iters; i++) {
    let node = root;

    // Selection
    while (node.untriedMoves.length === 0 && node.children.length > 0) {
      let bestChild = node.children[0];
      let bestValue = -Infinity;
      const C = 1.414;

      for (const child of node.children) {
        const exploitation = child.visits === 0 ? 0 : child.wins / child.visits;
        const exploration = C * Math.sqrt(Math.log(node.visits) / (child.visits + 1e-6));
        const bias = child.heuristicScore / (10 * (child.visits + 1));
        const value = exploitation + exploration + bias;

        if (value > bestValue) {
          bestValue = value;
          bestChild = child;
        }
      }
      node = bestChild;
    }

    // Expansion
    if (node.untriedMoves.length > 0) {
      const nextPlayer: Player = node.player === 'B' ? 'W' : 'B';
      let bestIdx = 0;
      let bestScore = -Infinity;

      const nodeContext = computeHeuristicContext(node.boardState);

      for (let j = 0; j < node.untriedMoves.length; j++) {
        const m = node.untriedMoves[j];
        let score = 0;
        if (m === 'PASS') {
          score = -5;
        } else {
          score = getMoveHeuristicScore(node.boardState, m, nextPlayer, node.history, nodeContext);
        }
        if (score > bestScore) {
          bestScore = score;
          bestIdx = j;
        }
      }

      const move = node.untriedMoves.splice(bestIdx, 1)[0];
      let nextBoard = node.boardState;
      let nextHistory = [...node.history];

      if (move !== 'PASS') {
        const playRes = playMove(node.boardState, move.x, move.y, nextPlayer, node.history);
        nextBoard = playRes.board;
        nextHistory.push(boardToHash(nextBoard));
      } else {
        nextHistory.push(boardToHash(nextBoard) + '-PASS');
      }

      const child: MctsNode = {
        move,
        player: nextPlayer,
        visits: 0,
        wins: 0,
        parent: node,
        children: [],
        untriedMoves: [],
        boardState: nextBoard,
        history: nextHistory,
        heuristicScore: bestScore
      };

      const childNextPlayer: Player = nextPlayer === 'B' ? 'W' : 'B';
      const childLegalMoves: (Point | 'PASS')[] = [];
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          if (checkMoveLegality(nextBoard, r, c, childNextPlayer, nextHistory).legal) {
            childLegalMoves.push({ x: r, y: c });
          }
        }
      }
      childLegalMoves.push('PASS');
      child.untriedMoves = childLegalMoves;

      node.children.push(child);
      node = child;
    }

    // Simulation (Playout)
    let tempBoard = node.boardState;
    let tempPlayer: Player = node.player === 'B' ? 'W' : 'B';
    let tempHistory = [...node.history];
    let consecutivePasses = 0;
    const maxPlayoutDepth = size === 9 ? 30 : size === 13 ? 40 : 50;

    for (let depth = 0; depth < maxPlayoutDepth; depth++) {
      const legals: (Point | 'PASS')[] = [];
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          if (checkMoveLegality(tempBoard, r, c, tempPlayer, tempHistory).legal) {
            legals.push({ x: r, y: c });
          }
        }
      }
      legals.push('PASS');

      let selectedMove: Point | 'PASS' = 'PASS';
      const captures: Point[] = [];
      const others: (Point | 'PASS')[] = [];

      for (const m of legals) {
        if (m === 'PASS') {
          others.push(m);
        } else {
          const opponent: Player = tempPlayer === 'B' ? 'W' : 'B';
          const adj = getAdjacentPoints(m.x, m.y, size);
          let wouldCapture = false;

          const simulatedTempBoard = tempBoard.map(row => [...row]);
          simulatedTempBoard[m.x][m.y] = tempPlayer;
          for (const p of adj) {
            if (simulatedTempBoard[p.x][p.y] === opponent) {
              const { liberties } = getGroupLiberties(simulatedTempBoard, p.x, p.y);
              if (liberties.length === 0) {
                wouldCapture = true;
                break;
              }
            }
          }

          if (wouldCapture) {
            captures.push(m);
          } else {
            others.push(m);
          }
        }
      }

      if (captures.length > 0 && Math.random() < 0.6) {
        selectedMove = captures[Math.floor(Math.random() * captures.length)];
      } else {
        selectedMove = others[Math.floor(Math.random() * others.length)];
      }

      if (selectedMove === 'PASS') {
        consecutivePasses++;
        tempHistory.push(boardToHash(tempBoard) + '-PASS');
      } else {
        consecutivePasses = 0;
        const playRes = playMove(tempBoard, selectedMove.x, selectedMove.y, tempPlayer, tempHistory);
        tempBoard = playRes.board;
        tempHistory.push(boardToHash(tempBoard));
      }

      if (consecutivePasses >= 2) {
        break;
      }
      tempPlayer = tempPlayer === 'B' ? 'W' : 'B';
    }

    const { blackTerritory, whiteTerritory } = calculateTerritory(tempBoard, new Set());
    let bStones = 0;
    let wStones = 0;
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (tempBoard[r][c] === 'B') bStones++;
        if (tempBoard[r][c] === 'W') wStones++;
      }
    }
    const bScore = bStones + blackTerritory.size;
    const wScore = wStones + whiteTerritory.size + 7.5;
    const winner: Player = bScore > wScore ? 'B' : 'W';

    // Backpropagation
    let curr: MctsNode | null = node;
    while (curr !== null) {
      curr.visits++;
      if (curr.player === winner) {
        curr.wins++;
      }
      curr = curr.parent;
    }
  }

  if (root.children.length === 0) {
    return 'PASS';
  }

  let bestChild = root.children[0];
  for (const child of root.children) {
    if (child.visits > bestChild.visits) {
      bestChild = child;
    }
  }

  return bestChild.move;
}

// Helper to format the Go board as a text grid
function formatBoardText(board: BoardState): string {
  const size = board.length;
  let text = '';
  // Column letters header
  const cols = [' '].concat(Array.from({ length: size }, (_, i) => indexToLabel(0, i, size)[0]));
  text += cols.join(' ') + '\n';
  
  for (let r = 0; r < size; r++) {
    const rowNum = size - r;
    const rowLabel = rowNum < 10 ? ` ${rowNum}` : `${rowNum}`;
    const rowCells = board[r].map(cell => {
      if (cell === 'B') return 'B';
      if (cell === 'W') return 'W';
      return '.';
    });
    text += `${rowLabel} ${rowCells.join(' ')}\n`;
  }
  return text;
}

// Helper function for fetch with timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = 12000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

// 2. Main API request router for Cloud LLM AIs
export async function getAiMove(
  board: BoardState,
  player: Player,
  boardHistory: string[],
  config: AiConfig
): Promise<Point | 'PASS'> {
  // Route to local offline options first
  if (config.provider === 'local') {
    return computeLocalHeuristicMove(board, player, boardHistory);
  }
  if (config.provider === 'mcts') {
    return computeMctsMove(board, player, boardHistory);
  }

  // If other providers require a key and it is missing, fallback to local heuristic
  if (!config.apiKey) {
    return computeLocalHeuristicMove(board, player, boardHistory);
  }

  const size = board.length;
  
  // Get all legal moves
  const legalPoints: Point[] = [];
  const legalLabels: string[] = [];
  
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (checkMoveLegality(board, r, c, player, boardHistory).legal) {
        legalPoints.push({ x: r, y: c });
        legalLabels.push(indexToLabel(r, c, size));
      }
    }
  }

  if (legalPoints.length === 0) {
    return 'PASS';
  }

  // Format prompt
  const playerColorName = player === 'B' ? 'Black (黑子)' : 'White (白子)';
  const boardText = formatBoardText(board);
  
  const systemPrompt = `You are playing a game of Go (圍棋) on a ${size}x${size} board. You are holding the ${playerColorName} stones.
Your goal is to choose the best next move.

Here is the current board state (B = Black, W = White, . = Empty):
${boardText}

LIST OF LEGAL MOVES:
${JSON.stringify(legalLabels)}

To pass your turn, choose "PASS".

Respond in strictly JSON format:
{
  "thought": "Brief explanation of your strategy and reasoning for this move in traditional Chinese (strictly under 100 characters)",
  "move": "Choose exactly one coordinate from the LIST OF LEGAL MOVES (e.g. D4, Q16) or 'PASS'"
}`;

  try {
    let resultMoveLabel = '';

    if (config.provider === 'gemini') {
      const modelName = config.model || 'gemini-1.5-flash';
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${config.apiKey}`;
      
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: systemPrompt }] }],
          generationConfig: {
            responseMimeType: 'application/json',
            temperature: 0.2
          }
        })
      }, 12000);

      if (!response.ok) {
        throw new Error(`Gemini API error: ${response.statusText}`);
      }

      const data = await response.json();
      const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
      const parsed = JSON.parse(text);
      resultMoveLabel = (parsed.move || '').toUpperCase().trim();

    } else if (config.provider === 'groq' || config.provider === 'openrouter' || config.provider === 'openai') {
      let url = '';
      if (config.provider === 'groq') {
        url = 'https://api.groq.com/openai/v1/chat/completions';
      } else if (config.provider === 'openrouter') {
        url = 'https://openrouter.ai/api/v1/chat/completions';
      } else {
        url = config.customProxyUrl?.trim() || 'https://api.openai.com/v1/chat/completions';
      }
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      };

      if (config.provider === 'openrouter') {
        headers['HTTP-Referer'] = window.location.origin;
        headers['X-Title'] = 'Go Board AI App';
      }

      const response = await fetchWithTimeout(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: config.model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: 'Choose the next move.' }
          ],
          response_format: { type: 'json_object' },
          temperature: 0.2
        })
      }, 12000);

      if (!response.ok) {
        throw new Error(`${config.provider} API error: ${response.statusText}`);
      }

      const data = await response.json();
      const text = data.choices?.[0]?.message?.content || '';
      const parsed = JSON.parse(text);
      resultMoveLabel = (parsed.move || '').toUpperCase().trim();

    } else if (config.provider === 'anthropic') {
      const url = config.customProxyUrl?.trim() || 'https://api.anthropic.com/v1/messages';
      
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': config.apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify({
          model: config.model,
          max_tokens: 400,
          system: systemPrompt,
          messages: [
            { role: 'user', content: 'Choose the next move. Respond strictly in JSON format.' }
          ],
          temperature: 0.2
        })
      }, 12000);

      if (!response.ok) {
        throw new Error(`Anthropic API error: ${response.statusText}`);
      }

      const data = await response.json();
      const text = data.content?.[0]?.text || '';
      
      let cleanedText = text.trim();
      const firstBrace = cleanedText.indexOf('{');
      const lastBrace = cleanedText.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1) {
        cleanedText = cleanedText.slice(firstBrace, lastBrace + 1);
      }
      
      const parsed = JSON.parse(cleanedText);
      resultMoveLabel = (parsed.move || '').toUpperCase().trim();
    }

    if (resultMoveLabel === 'PASS') {
      return 'PASS';
    }

    const matchedIndex = legalLabels.indexOf(resultMoveLabel);
    if (matchedIndex !== -1) {
      return legalPoints[matchedIndex];
    } else {
      console.warn(`AI suggested illegal/unrecognized move: ${resultMoveLabel}. Falling back to local heuristic.`);
    }

  } catch (error) {
    console.error('Failed to query cloud AI, falling back to local heuristic:', error);
  }

  return computeLocalHeuristicMove(board, player, boardHistory);
}

// 3. API Key Validator
export async function validateApiKey(
  provider: 'gemini' | 'groq' | 'openrouter' | 'openai' | 'anthropic',
  apiKey: string,
  customProxyUrl?: string
): Promise<{ valid: boolean; message: string }> {
  if (!apiKey.trim()) {
    return { valid: false, message: 'API 金鑰不能為空 (API Key cannot be empty)' };
  }

  try {
    if (provider === 'gemini') {
      const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`;
      const res = await fetch(url);
      if (res.ok) {
        return { valid: true, message: '驗證成功！此 Gemini 金鑰有效。' };
      } else {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || res.statusText;
        return { valid: false, message: `驗證失敗：${errMsg}` };
      }
    } else if (provider === 'groq') {
      const url = 'https://api.groq.com/openai/v1/models';
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });
      if (res.ok) {
        return { valid: true, message: '驗證成功！此 Groq 金鑰有效。' };
      } else {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || res.statusText;
        return { valid: false, message: `驗證失敗：${errMsg}` };
      }
    } else if (provider === 'openrouter') {
      const url = 'https://openrouter.ai/api/v1/key';
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        const label = data.data?.label || 'Unnamed';
        const limitStr = data.data?.limit_remaining !== undefined ? `，剩餘額度：$${data.data.limit_remaining}` : '';
        return { valid: true, message: `驗證成功！此 OpenRouter 金鑰有效 (標籤: ${label}${limitStr})。` };
      } else {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || res.statusText;
        return { valid: false, message: `驗證失敗：${errMsg}` };
      }
    } else if (provider === 'openai') {
      let url = 'https://api.openai.com/v1/models';
      if (customProxyUrl) {
        url = customProxyUrl.replace('/chat/completions', '/models');
      }
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });
      if (res.ok) {
        return { valid: true, message: '驗證成功！此 OpenAI 金鑰有效。' };
      } else {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || res.statusText;
        return { valid: false, message: `驗證失敗：${errMsg}` };
      }
    } else if (provider === 'anthropic') {
      const url = customProxyUrl?.trim() || 'https://api.anthropic.com/v1/messages';
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify({
          model: 'claude-3-5-haiku-latest',
          max_tokens: 1,
          messages: [{ role: 'user', content: 'Ping' }]
        })
      });
      if (res.ok || res.status === 400 || res.status === 429) {
        if (res.status === 401) {
          return { valid: false, message: '驗證失敗：API 金鑰無效 (Unauthorized)。' };
        }
        return { valid: true, message: '驗證成功！此 Anthropic 金鑰有效。' };
      } else {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || res.statusText;
        return { valid: false, message: `驗證失敗：${errMsg}` };
      }
    }
    return { valid: false, message: '不支援的 AI 供應商' };
  } catch (error: any) {
    return { valid: false, message: `連線失敗：${error.message || error}` };
  }
}

