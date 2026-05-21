import { describe, it, expect } from 'vitest';
import {
  createEmptyBoard,
  playMove,
  checkMoveLegality,
  getGroupLiberties,
  calculateScore
} from './goEngine';
import type { BoardState } from './goEngine';

describe('Go Board Logic & Rules Engine', () => {
  
  it('should initialize an empty board with correct dimensions', () => {
    const board = createEmptyBoard(9);
    expect(board.length).toBe(9);
    expect(board[0].length).toBe(9);
    expect(board[0][0]).toBeNull();
  });

  it('should compute liberties correctly for a single stone', () => {
    // Put a black stone in the center of 9x9 (4,4)
    let board = createEmptyBoard(9);
    board[4][4] = 'B';
    
    const { liberties } = getGroupLiberties(board, 4, 4);
    // Center stone should have 4 liberties (up, down, left, right)
    expect(liberties.length).toBe(4);
    
    // Put a black stone at the corner (0,0)
    board = createEmptyBoard(9);
    board[0][0] = 'B';
    const { liberties: cornerLiberties } = getGroupLiberties(board, 0, 0);
    // Corner stone should have 2 liberties
    expect(cornerLiberties.length).toBe(2);
  });

  it('should compute liberties correctly for connected groups', () => {
    let board = createEmptyBoard(9);
    board[4][4] = 'B';
    board[4][5] = 'B'; // connected horizontally
    
    const { stones, liberties } = getGroupLiberties(board, 4, 4);
    expect(stones.length).toBe(2);
    // 2 horizontal stones in the center should have 6 liberties
    expect(liberties.length).toBe(6);
  });

  it('should capture single stone when liberties are reduced to zero', () => {
    // Setup: Black stone at (0,1), surrounded by White at (0,0), (0,2), (1,1)
    let board = createEmptyBoard(9);
    board[0][1] = 'B'; // Target stone
    
    board[0][0] = 'W';
    board[0][2] = 'W';
    // The final surrounding stone will be placed at (1,1) by White
    
    const history: string[] = [];
    const result = playMove(board, 1, 1, 'W', history);
    
    expect(result.legal).toBe(true);
    expect(result.captured.length).toBe(1);
    expect(result.captured[0]).toEqual({ x: 0, y: 1 });
    // The captured black stone should be removed from board
    expect(result.board[0][1]).toBeNull();
  });

  it('should prevent suicide moves unless they result in a capture', () => {
    // Setup: White surrounds empty cell (0,0) at (0,1) and (1,0)
    let board = createEmptyBoard(9);
    board[0][1] = 'W';
    board[1][0] = 'W';
    
    const history: string[] = [];
    // Black trying to play (0,0) is a suicide because it has 0 liberties and captures nothing
    const blackLegality = checkMoveLegality(board, 0, 0, 'B', history);
    expect(blackLegality.legal).toBe(false);
    expect(blackLegality.reason).toContain('Suicide');

    // However, if White tries to play (0,0), it is legal since White stones are adjacent (connecting to liberties)
    const whiteLegality = checkMoveLegality(board, 0, 0, 'W', history);
    expect(whiteLegality.legal).toBe(true);
  });

  it('should allow suicide-like move if it results in a capture', () => {
    // Setup: White group around (0,0) at (0,1) and (1,0) but White has no other liberties
    // Black stone at (0,0). White stones at (0,1) and (1,0). 
    // If Black is surrounded by White, but White's surrounding stones also have 0 liberties,
    // playing the final stone to surround White is legal and captures White!
    let board = createEmptyBoard(9);
    // Put White stones at (0,1) and (1,0)
    board[0][1] = 'W';
    board[1][0] = 'W';
    // Surround White stones with Black
    board[0][2] = 'B';
    board[1][1] = 'B';
    board[2][0] = 'B';
    
    // Now (0,0) is empty. If White plays (0,0), it captures the Black stones? No,
    // If Black plays (0,0), it has 0 liberties but captures the White stones (0,1) and (1,0).
    const history: string[] = [];
    const result = playMove(board, 0, 0, 'B', history);
    
    expect(result.legal).toBe(true);
    expect(result.captured.length).toBe(2); // Captures both White stones
    expect(result.board[0][1]).toBeNull();
    expect(result.board[1][0]).toBeNull();
  });

  it('should enforce the Ko rule', () => {
    // Setup standard Ko shape
    // Black: (0,2), (2,2), (1,3)
    // White: (0,1), (2,1), (1,0), (1,2)
    // Empty center/captured spaces: (1,1) and (1,2)
    let board = createEmptyBoard(9);
    board[0][2] = 'B';
    board[2][2] = 'B';
    board[1][3] = 'B';
    
    board[0][1] = 'W';
    board[2][1] = 'W';
    board[1][0] = 'W';
    board[1][2] = 'W'; // White stone to be captured
    
    let history: string[] = [boardToHash(board)];

    // 1. Black plays (1,1) capturing White (1,2)
    const res1 = playMove(board, 1, 1, 'B', history);
    expect(res1.legal).toBe(true);
    expect(res1.captured.length).toBe(1);
    expect(res1.captured[0]).toEqual({ x: 1, y: 2 });
    
    const boardState1 = res1.board;
    const hash1 = boardToHash(boardState1);
    history.push(hash1);

    // Now White immediately trying to capture back at (1,2) is a Ko violation
    const whiteLegality = checkMoveLegality(boardState1, 1, 2, 'W', history);
    expect(whiteLegality.legal).toBe(false);
    expect(whiteLegality.reason).toContain('Ko');
  });

  it('should compute scores correctly for Chinese and Japanese rules', () => {
    // 9x9 board, Black has 4 stones and surrounds 2 points. White has 3 stones and surrounds 1 point.
    // Chinese rules: Black area = 4 stones + 2 territory = 6. White area = 3 stones + 1 territory = 4 + Komi.
    // Japanese rules: Black = 2 territory - prisoners. White = 1 territory - prisoners + Komi.
    let board = createEmptyBoard(9);
    
    // Black stones surrounding (0,0) and (0,1)
    board[0][2] = 'B';
    board[1][0] = 'B';
    board[1][1] = 'B';
    board[1][2] = 'B';
    
    // White stones surrounding (8,8)
    board[8][7] = 'W';
    board[7][8] = 'W';
    board[7][7] = 'W';

    const deadStones = new Set<string>();
    
    const chScore = calculateScore(board, deadStones, 'Chinese', 7.5, 0, 0);
    expect(chScore.blackStonesCount).toBe(4);
    expect(chScore.blackTerritoryCount).toBe(2); // (0,0) and (0,1) are surrounded by Black
    expect(chScore.blackScore).toBe(6);
    expect(chScore.whiteStonesCount).toBe(3);
    expect(chScore.whiteTerritoryCount).toBe(1); // (8,8) is surrounded by White
    expect(chScore.whiteScore).toBe(4 + 7.5);

    const jpScore = calculateScore(board, deadStones, 'Japanese', 6.5, 2, 1);
    // Black: 2 territory - 2 prisoners = 0
    expect(jpScore.blackScore).toBe(0);
    // White: 1 territory - 1 prisoner + 6.5 komi = 6.5
    expect(jpScore.whiteScore).toBe(1 - 1 + 6.5);
  });
});

// Helper for Ko test
function boardToHash(board: BoardState): string {
  return board.map(row => row.map(cell => cell || '.').join('')).join('');
}
