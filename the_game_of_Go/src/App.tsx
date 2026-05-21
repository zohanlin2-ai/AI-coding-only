import React, { useState, useEffect, useRef } from 'react';
import { SetupPanel, getHandicapPoints } from './components/SetupPanel';
import { GoBoard } from './components/GoBoard';
import {
  type BoardState,
  type Player,
  type Point,
  createEmptyBoard,
  playMove,
  calculateScore,
  calculateTerritory
} from './utils/goEngine';
import { getAiMove, type AiConfig } from './services/aiService';
import { exportToSgf, importFromSgf } from './utils/sgfParser';

interface PlayerState {
  type: 'human' | 'ai';
  aiConfig: AiConfig;
}

export const App: React.FC = () => {
  // Game state mode: SETUP (menu), PLAYING, SCORING
  const [gameState, setGameState] = useState<'SETUP' | 'PLAYING' | 'SCORING'>('SETUP');

  // Game rules configuration
  const [boardSize, setBoardSize] = useState<number>(19);
  const [rules, setRules] = useState<'Chinese' | 'Japanese'>('Chinese');
  const [handicap, setHandicap] = useState<number>(0);
  const [komi, setKomi] = useState<number>(7.5);

  const [blackPlayer, setBlackPlayer] = useState<PlayerState>({
    type: 'human',
    aiConfig: { provider: 'local', model: 'gemini-2.5-flash', apiKey: '' }
  });
  const [whitePlayer, setWhitePlayer] = useState<PlayerState>({
    type: 'human',
    aiConfig: { provider: 'local', model: 'gemini-2.5-flash', apiKey: '' }
  });

  // Active board game state
  const [board, setBoard] = useState<BoardState>(createEmptyBoard(19));
  const [turn, setTurn] = useState<Player>('B');
  const [lastMove, setLastMove] = useState<Point | null>(null);
  
  // History tracking
  const [boardHistory, setBoardHistory] = useState<string[]>([]);
  const [moves, setMoves] = useState<{ player: Player; x: number; y: number; isPass: boolean }[]>([]);

  // Capture counts (prisoners)
  const [capturedBlackCount, setCapturedBlackCount] = useState<number>(0); // Captured by White
  const [capturedWhiteCount, setCapturedWhiteCount] = useState<number>(0); // Captured by Black

  // Consective passes counter
  const [passCount, setPassCount] = useState<number>(0);

  // AI Thinking state
  const [isAiThinking, setIsAiThinking] = useState<boolean>(false);

  // Scoring details
  const [deadStones, setDeadStones] = useState<Set<string>>(new Set());
  const [blackTerritory, setBlackTerritory] = useState<Set<string>>(new Set());
  const [whiteTerritory, setWhiteTerritory] = useState<Set<string>>(new Set());
  
  // Refs to avoid state staleness in AI trigger loop
  const triggerTimeoutRef = useRef<number | null>(null);
  const lastProcessedRef = useRef<string>('');

  // Triggers AI moves when game is playing and it's an AI's turn
  useEffect(() => {
    if (gameState !== 'PLAYING') return;

    const currentPlayer = turn === 'B' ? blackPlayer : whitePlayer;
    if (currentPlayer.type === 'human') return;

    // Generate unique state key for current board configuration and turn
    const boardHash = board.map(row => row.map(c => c || '.').join('')).join('');
    const stateKey = `${turn}-${boardHash}`;

    // Avoid double-processing the same board state
    if (lastProcessedRef.current === stateKey) return;

    lastProcessedRef.current = stateKey;
    setIsAiThinking(true);
    
    // Clean up older timeouts
    if (triggerTimeoutRef.current) window.clearTimeout(triggerTimeoutRef.current);

    triggerTimeoutRef.current = window.setTimeout(async () => {
      try {
        const move = await getAiMove(board, turn, boardHistory, currentPlayer.aiConfig);
        
        if (move === 'PASS') {
          handlePass();
        } else {
          executeMove(move.x, move.y);
        }
      } catch (err) {
        console.error('AI move execution failed, falling back to PASS:', err);
        handlePass();
      } finally {
        setIsAiThinking(false);
      }
    }, 900);

    return () => {
      if (triggerTimeoutRef.current) window.clearTimeout(triggerTimeoutRef.current);
    };
  }, [gameState, turn, board, blackPlayer, whitePlayer, boardHistory]);

  // Scoring mode: update territories dynamically when dead stones list updates
  useEffect(() => {
    if (gameState !== 'SCORING') return;
    const { blackTerritory: bt, whiteTerritory: wt } = calculateTerritory(board, deadStones);
    setBlackTerritory(bt);
    setWhiteTerritory(wt);
  }, [gameState, board, deadStones]);

  // Setup game callback
  const handleStartGame = (config: {
    boardSize: number;
    rules: 'Chinese' | 'Japanese';
    handicap: number;
    komi: number;
    blackPlayer: PlayerState;
    whitePlayer: PlayerState;
  }) => {
    const size = config.boardSize;
    let initialBoard = createEmptyBoard(size);
    
    // Place Handicap stones
    const handicapPoints = getHandicapPoints(size, config.handicap);
    for (const p of handicapPoints) {
      initialBoard[p.x][p.y] = 'B';
    }

    setBoardSize(size);
    setRules(config.rules);
    setHandicap(config.handicap);
    setKomi(config.komi);
    setBlackPlayer(config.blackPlayer);
    setWhitePlayer(config.whitePlayer);

    setBoard(initialBoard);
    // If handicap, White plays first (except 1 handicap which is just black even game)
    setTurn(config.handicap >= 2 ? 'W' : 'B');
    setLastMove(null);
    setBoardHistory([initialBoard.map(row => row.map(c => c || '.').join('')).join('')]);
    setMoves([]);
    setCapturedBlackCount(0);
    setCapturedWhiteCount(0);
    setPassCount(0);
    setDeadStones(new Set());
    
    setGameState('PLAYING');
  };

  // Perform a legal stone placement
  const executeMove = (x: number, y: number) => {
    const result = playMove(board, x, y, turn, boardHistory);
    if (!result.legal) {
      return false;
    }

    // Play move success
    setBoard(result.board);
    setLastMove({ x, y });

    // Track captures
    if (result.captured.length > 0) {
      if (turn === 'B') {
        setCapturedWhiteCount(prev => prev + result.captured.length);
      } else {
        setCapturedBlackCount(prev => prev + result.captured.length);
      }
    }

    // Add to history
    const nextHash = result.board.map(row => row.map(c => c || '.').join('')).join('');
    setBoardHistory(prev => [...prev, nextHash]);
    setMoves(prev => [...prev, { player: turn, x, y, isPass: false }]);
    
    // Toggle turn and reset passes
    setTurn(turn === 'B' ? 'W' : 'B');
    setPassCount(0);
    return true;
  };

  // Human click placement handler
  const handlePlayMove = (x: number, y: number) => {
    const currentPlayer = turn === 'B' ? blackPlayer : whitePlayer;
    if (currentPlayer.type === 'ai') return; // Ignore if AI turn

    executeMove(x, y);
  };

  // Pass move handler
  const handlePass = () => {
    const nextPassCount = passCount + 1;
    setPassCount(nextPassCount);
    setMoves(prev => [...prev, { player: turn, x: -1, y: -1, isPass: true }]);
    
    setTurn(turn === 'B' ? 'W' : 'B');
    setLastMove(null);

    // If two consecutive passes, enter scoring
    if (nextPassCount >= 2) {
      enterScoringMode();
    }
  };

  // Enter final scoring
  const enterScoringMode = () => {
    // Collect auto-detected dead stones
    // For simplicity, auto-detect dead stones as isolated stones that are enclosed
    // We start deadStones as empty and let users click, which is safest.
    setDeadStones(new Set());
    setGameState('SCORING');
  };

  // Resign move handler
  const handleResign = () => {
    const winner = turn === 'B' ? 'White' : 'Black';
    alert(`${turn === 'B' ? '黑方 (Black)' : '白方 (White)'} 投降！\n恭喜 ${winner === 'Black' ? '黑方' : '白方'} 獲得勝利！`);
    setGameState('SETUP');
  };

  // Toggle alive/dead stone status in scoring mode
  const handleToggleDeadStone = (x: number, y: number) => {
    const key = `${x},${y}`;
    setDeadStones(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Export SGF file
  const handleExportSgf = () => {
    const handicapPoints = getHandicapPoints(boardSize, handicap);
    const sgfContent = exportToSgf({
      boardSize,
      rules,
      komi,
      blackPlayerName: blackPlayer.type === 'ai' ? `AI (${blackPlayer.aiConfig.provider})` : 'Black',
      whitePlayerName: whitePlayer.type === 'ai' ? `AI (${whitePlayer.aiConfig.provider})` : 'White',
      handicapStones: handicapPoints,
      moves: moves
    });

    const blob = new Blob([sgfContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `go-game-${Date.now()}.sgf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Import SGF file
  const handleImportSgf = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = importFromSgf(text);
        
        // Setup game based on parsed info
        setBoardSize(parsed.boardSize);
        setRules(parsed.rules);
        setKomi(parsed.komi);
        
        // Rebuild player info
        setBlackPlayer({
          type: 'human',
          aiConfig: { provider: 'local', model: 'gemini-2.5-flash', apiKey: '' }
        });
        setWhitePlayer({
          type: 'human',
          aiConfig: { provider: 'local', model: 'gemini-2.5-flash', apiKey: '' }
        });

        // Replay moves to build board state
        let tempBoard = createEmptyBoard(parsed.boardSize);
        
        // Place handicap stones
        for (const p of parsed.handicapStones) {
          tempBoard[p.x][p.y] = 'B';
        }

        let tempHistory = [tempBoard.map(row => row.map(c => c || '.').join('')).join('')];
        let blackCaptured = 0;
        let whiteCaptured = 0;
        let lastPt: Point | null = null;
        let consecutivePasses = 0;

        for (const move of parsed.moves) {
          if (move.isPass) {
            consecutivePasses++;
            lastPt = null;
          } else {
            consecutivePasses = 0;
            const res = playMove(tempBoard, move.x, move.y, move.player, tempHistory);
            if (res.legal) {
              tempBoard = res.board;
              lastPt = { x: move.x, y: move.y };
              if (res.captured.length > 0) {
                if (move.player === 'B') whiteCaptured += res.captured.length;
                else blackCaptured += res.captured.length;
              }
              tempHistory.push(tempBoard.map(row => row.map(c => c || '.').join('')).join(''));
            }
          }
        }

        setBoard(tempBoard);
        setBoardHistory(tempHistory);
        setMoves(parsed.moves);
        setCapturedBlackCount(blackCaptured);
        setCapturedWhiteCount(whiteCaptured);
        setLastMove(lastPt);
        setPassCount(consecutivePasses);

        // Set next turn
        if (parsed.moves.length > 0) {
          const lastPlayer = parsed.moves[parsed.moves.length - 1].player;
          setTurn(lastPlayer === 'B' ? 'W' : 'B');
        } else {
          setTurn(parsed.handicapStones.length >= 2 ? 'W' : 'B');
        }

        setDeadStones(new Set());
        setGameState(consecutivePasses >= 2 ? 'SCORING' : 'PLAYING');

      } catch (err) {
        console.error('SGF parsing error:', err);
        alert('載入 SGF 檔案失敗，請確認檔案格式是否正確。');
      }
    };
    reader.readAsText(file);
    // Reset file input value so same file can be reloaded if needed
    e.target.value = '';
  };

  // Score calculations
  const scores = calculateScore(board, deadStones, rules, komi, capturedBlackCount, capturedWhiteCount);
  const isBlackWinning = scores.blackScore > scores.whiteScore;
  const scoreDiff = Math.abs(scores.blackScore - scores.whiteScore);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      
      {/* Dynamic Glow Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo" />
          <h1 className="brand-title">碁鋒 Go App</h1>
        </div>
        {gameState !== 'SETUP' && (
          <button className="btn btn-secondary" onClick={() => setGameState('SETUP')}>
            返回設定
          </button>
        )}
      </header>

      {gameState === 'SETUP' ? (
        <SetupPanel onStartGame={handleStartGame} />
      ) : (
        <main className="game-layout">
          
          {/* Black Player Sidebar */}
          <section className={`player-sidebar-card glass-panel ${turn === 'B' && gameState === 'PLAYING' ? 'active-turn' : ''}`}>
            <div className="sidebar-player-title">
              <span>黑方 (Black)</span>
              <span className={`sidebar-badge ${blackPlayer.type === 'ai' ? (isAiThinking && turn === 'B' ? 'active-thinking' : 'ai') : 'human'}`}>
                {blackPlayer.type === 'ai' ? (isAiThinking && turn === 'B' ? 'AI 思考中' : 'AI') : '手動'}
              </span>
            </div>

            <div className="stat-row">
              <span className="stat-label">棋子顏色</span>
              <span className="stat-value">黑子 (●)</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">提子數量 (Prisoners)</span>
              <span className="stat-value">{capturedWhiteCount}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">下子類型</span>
              <span className="stat-value">
                {blackPlayer.type === 'ai' 
                  ? `${blackPlayer.aiConfig.provider === 'local' ? '本地 Heuristic' : blackPlayer.aiConfig.provider.toUpperCase()}` 
                  : '手動玩家'}
              </span>
            </div>

            {blackPlayer.type === 'ai' && blackPlayer.aiConfig.provider !== 'local' && (
              <div className="thought-bubble">
                <strong>AI 策略思考：</strong>
                <p>
                  {isAiThinking && turn === 'B' 
                    ? '正在研擬下一步棋的配置...' 
                    : '已完成落子分析。'}
                </p>
              </div>
            )}
          </section>

          {/* Core Go Board Column */}
          <section className="board-container">
            
            {/* If in Scoring mode, display a detailed breakdown card */}
            {gameState === 'SCORING' && (
              <div className="scoring-hud-wrapper glass-panel" style={{ width: '100%' }}>
                <h3 className="scoring-title">棋局結算進行中</h3>
                <p className="scoring-helper-txt">
                  系統已自動偵測雙方領地。如果有被包圍且無眼位活路的死子仍留在盤上，請點擊它們將其淡出（標記為死子），得分將自動即時重算。
                </p>
                
                <div className="scoring-math-grid">
                  <div>
                    <h4 className="math-col-title">
                      <span className="stone-dot black" /> 黑方得分 ({rules === 'Chinese' ? '數子法' : '比目法'})
                    </h4>
                    <div className="scoring-math-formula">
                      {rules === 'Chinese' ? (
                        <>
                          <span>• 盤上活子：{scores.blackStonesCount} 子</span>
                          <span>• 圍得地盤：{scores.blackTerritoryCount} 點</span>
                          <span style={{ fontWeight: 'bold', borderTop: '1px solid #2e303a', paddingTop: '0.25rem', marginTop: '0.25rem' }}>
                            總得分 = {scores.blackScore.toFixed(1)} 分
                          </span>
                        </>
                      ) : (
                        <>
                          <span>• 圍得地盤：{scores.blackTerritoryCount} 目</span>
                          <span>• 損失死子與提子：{capturedBlackCount + Array.from(deadStones).filter(k => board[parseInt(k.split(',')[0], 10)][parseInt(k.split(',')[1], 10)] === 'B').length} 子</span>
                          <span style={{ fontWeight: 'bold', borderTop: '1px solid #2e303a', paddingTop: '0.25rem', marginTop: '0.25rem' }}>
                            總得分 = {scores.blackScore.toFixed(1)} 分
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="math-col-title">
                      <span className="stone-dot white" /> 白方得分 (含貼目 {komi})
                    </h4>
                    <div className="scoring-math-formula">
                      {rules === 'Chinese' ? (
                        <>
                          <span>• 盤上活子：{scores.whiteStonesCount} 子</span>
                          <span>• 圍得地盤：{scores.whiteTerritoryCount} 點</span>
                          <span>• 規則貼目：+{komi} 分</span>
                          <span style={{ fontWeight: 'bold', borderTop: '1px solid #2e303a', paddingTop: '0.25rem', marginTop: '0.25rem' }}>
                            總得分 = {scores.whiteScore.toFixed(1)} 分
                          </span>
                        </>
                      ) : (
                        <>
                          <span>• 圍得地盤：{scores.whiteTerritoryCount} 目</span>
                          <span>• 損失死子與提子：{capturedWhiteCount + Array.from(deadStones).filter(k => board[parseInt(k.split(',')[0], 10)][parseInt(k.split(',')[1], 10)] === 'W').length} 子</span>
                          <span>• 規則貼目：+{komi} 目</span>
                          <span style={{ fontWeight: 'bold', borderTop: '1px solid #2e303a', paddingTop: '0.25rem', marginTop: '0.25rem' }}>
                            總得分 = {scores.whiteScore.toFixed(1)} 分
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="scoring-result-banner">
                  結果：{isBlackWinning ? '黑方' : '白方'} 淨勝 {scoreDiff.toFixed(1)} {rules === 'Chinese' ? '子' : '目'}！
                </div>
              </div>
            )}

            {/* Render Canvas Go Board */}
            <div className="canvas-board-wrapper">
              <GoBoard
                board={board}
                boardSize={boardSize}
                turn={turn}
                lastMove={lastMove}
                scoringMode={gameState === 'SCORING'}
                deadStones={deadStones}
                blackTerritory={blackTerritory}
                whiteTerritory={whiteTerritory}
                onPlayMove={handlePlayMove}
                onToggleDeadStone={handleToggleDeadStone}
                isPending={isAiThinking}
                interactive={
                  gameState === 'PLAYING' &&
                  ((turn === 'B' && blackPlayer.type === 'human') ||
                   (turn === 'W' && whitePlayer.type === 'human'))
                }
              />

              {/* Loader overlay during AI thought processing */}
              {isAiThinking && (
                <div className="board-message-overlay">
                  <span className="spinner" style={{ width: '40px', height: '40px', borderWidth: '3px' }} />
                  <span className="board-message-title">AI 正在落子運算中...</span>
                </div>
              )}
            </div>

            {/* Bottom Controls panel */}
            <div className="game-controls">
              {gameState === 'PLAYING' ? (
                <>
                  <div className="game-status-banner">
                    {turn === 'B' ? (
                      <>
                        <span className="stone-dot black" />
                        <span>輪到黑方下子</span>
                      </>
                    ) : (
                      <>
                        <span className="stone-dot white" />
                        <span>輪到白方下子</span>
                      </>
                    )}
                  </div>
                  
                  <button 
                    className="btn btn-secondary" 
                    onClick={handlePass}
                    disabled={isAiThinking}
                  >
                    虛手 (Pass)
                  </button>
                  <button 
                    className="btn btn-danger" 
                    onClick={handleResign}
                    disabled={isAiThinking}
                  >
                    投降 (Resign)
                  </button>
                </>
              ) : (
                <button className="btn btn-success" onClick={() => setGameState('SETUP')}>
                  完成計算，返回設定
                </button>
              )}

              {/* SGF I/O Actions */}
              <button className="btn btn-secondary" onClick={handleExportSgf}>
                匯出 SGF 棋譜
              </button>
              
              <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                匯入 SGF 棋譜
                <input 
                  type="file" 
                  accept=".sgf" 
                  style={{ display: 'none' }} 
                  onChange={handleImportSgf} 
                />
              </label>
            </div>

          </section>

          {/* White Player Sidebar */}
          <section className={`player-sidebar-card glass-panel ${turn === 'W' && gameState === 'PLAYING' ? 'active-turn' : ''}`}>
            <div className="sidebar-player-title">
              <span>白方 (White)</span>
              <span className={`sidebar-badge ${whitePlayer.type === 'ai' ? (isAiThinking && turn === 'W' ? 'active-thinking' : 'ai') : 'human'}`}>
                {whitePlayer.type === 'ai' ? (isAiThinking && turn === 'W' ? 'AI 思考中' : 'AI') : '手動'}
              </span>
            </div>

            <div className="stat-row">
              <span className="stat-label">棋子顏色</span>
              <span className="stat-value">白子 (○)</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">提子數量 (Prisoners)</span>
              <span className="stat-value">{capturedBlackCount}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">下子類型</span>
              <span className="stat-value">
                {whitePlayer.type === 'ai' 
                  ? `${whitePlayer.aiConfig.provider === 'local' ? '本地 Heuristic' : whitePlayer.aiConfig.provider.toUpperCase()}` 
                  : '手動玩家'}
              </span>
            </div>

            {whitePlayer.type === 'ai' && whitePlayer.aiConfig.provider !== 'local' && (
              <div className="thought-bubble">
                <strong>AI 策略思考：</strong>
                <p>
                  {isAiThinking && turn === 'W' 
                    ? '正在研擬下一步棋的配置...' 
                    : '已完成落子分析。'}
                </p>
              </div>
            )}
          </section>

        </main>
      )}
    </div>
  );
};
