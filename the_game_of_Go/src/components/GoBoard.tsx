import React, { useRef, useEffect, useState } from 'react';
import { type BoardState, type Player, type Point, COLS_LETTER } from '../utils/goEngine';

interface GoBoardProps {
  board: BoardState;
  boardSize: number;
  turn: Player;
  lastMove: Point | null;
  scoringMode: boolean;
  deadStones: Set<string>;
  blackTerritory: Set<string>;
  whiteTerritory: Set<string>;
  onPlayMove: (x: number, y: number) => void;
  onToggleDeadStone: (x: number, y: number) => void;
  isPending: boolean;
  interactive: boolean; // False if AI's turn
}

export const GoBoard: React.FC<GoBoardProps> = ({
  board,
  boardSize,
  turn,
  lastMove,
  scoringMode,
  deadStones,
  blackTerritory,
  whiteTerritory,
  onPlayMove,
  onToggleDeadStone,
  isPending,
  interactive
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoverPt, setHoverPt] = useState<Point | null>(null);

  // Redraw board whenever state changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas dimensions with high-DPI retina display support
    const size = 560;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    // Padding around board grid for coordinates
    const padding = 32;
    const gridArea = size - padding * 2;
    const step = gridArea / (boardSize - 1);

    // Helper to map index to canvas x/y coordinate
    const getCoord = (idx: number) => padding + idx * step;

    // 1. Draw Wooden Background
    // Kaya wood gradient
    const bgGrad = ctx.createRadialGradient(size / 2, size / 2, 50, size / 2, size / 2, size);
    bgGrad.addColorStop(0, '#f3be7a');
    bgGrad.addColorStop(1, '#d3984d');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, size, size);

    // Subtle wood grain ring simulation
    ctx.strokeStyle = 'rgba(82, 59, 28, 0.04)';
    ctx.lineWidth = 1;
    for (let radius = 100; radius < size * 1.2; radius += 40) {
      ctx.beginPath();
      ctx.arc(size / 2 - 50, size / 2 - 50, radius, 0.1, 1.4);
      ctx.stroke();
    }

    // 2. Draw Coordinates Labels (A, B, C... and 1, 2, 3...)
    ctx.fillStyle = '#523b1c';
    ctx.font = '500 11px Space Grotesk, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < boardSize; i++) {
      const coord = getCoord(i);
      const label = COLS_LETTER[i];
      const rowLabel = (boardSize - i).toString();

      // Horizontal labels (columns) - Top & Bottom
      ctx.fillText(label, coord, padding / 2);
      ctx.fillText(label, coord, size - padding / 2);

      // Vertical labels (rows) - Left & Right
      ctx.fillText(rowLabel, padding / 2, coord);
      ctx.fillText(rowLabel, size - padding / 2, coord);
    }

    // 3. Draw Grid Lines
    ctx.strokeStyle = '#523b1c';
    ctx.lineWidth = 1;
    
    // Draw horizontal lines
    for (let r = 0; r < boardSize; r++) {
      ctx.beginPath();
      ctx.moveTo(padding, getCoord(r));
      ctx.lineTo(size - padding, getCoord(r));
      ctx.stroke();
    }

    // Draw vertical lines
    for (let c = 0; c < boardSize; c++) {
      ctx.beginPath();
      ctx.moveTo(getCoord(c), padding);
      ctx.lineTo(getCoord(c), size - padding);
      ctx.stroke();
    }

    // 4. Draw Star Points (星位)
    const drawStar = (x: number, y: number) => {
      ctx.fillStyle = '#423016';
      ctx.beginPath();
      ctx.arc(getCoord(x), getCoord(y), boardSize === 9 ? 3 : 4, 0, Math.PI * 2);
      ctx.fill();
    };

    if (boardSize === 19) {
      const stars = [3, 9, 15];
      for (const r of stars) {
        for (const c of stars) {
          drawStar(r, c);
        }
      }
    } else if (boardSize === 13) {
      const stars = [3, 6, 9];
      for (const r of stars) {
        for (const c of stars) {
          // 13x13 has star points at corners and center
          drawStar(r, c);
        }
      }
    } else if (boardSize === 9) {
      // 9x9 has star points at 4 corners (2,2), (2,6), (6,2), (6,6) and center (4,4)
      const stars = [2, 6];
      for (const r of stars) {
        for (const c of stars) {
          drawStar(r, c);
        }
      }
      drawStar(4, 4);
    }

    // 5. Draw Territory Shading (if in scoring mode)
    if (scoringMode) {
      for (let r = 0; r < boardSize; r++) {
        for (let c = 0; c < boardSize; c++) {
          const key = `${r},${c}`;
          const isBlack = blackTerritory.has(key);
          const isWhite = whiteTerritory.has(key);
          
          if (isBlack || isWhite) {
            ctx.fillStyle = isBlack ? 'rgba(0, 0, 0, 0.45)' : 'rgba(255, 255, 255, 0.55)';
            const sizeBox = step * 0.45;
            ctx.fillRect(
              getCoord(c) - sizeBox / 2,
              getCoord(r) - sizeBox / 2,
              sizeBox,
              sizeBox
            );
            ctx.strokeStyle = isBlack ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.9)';
            ctx.lineWidth = 1;
            ctx.strokeRect(
              getCoord(c) - sizeBox / 2,
              getCoord(r) - sizeBox / 2,
              sizeBox,
              sizeBox
            );
          }
        }
      }
    }

    // 6. Draw Stones
    const stoneRadius = (step / 2) * 0.95;

    for (let r = 0; r < boardSize; r++) {
      for (let c = 0; c < boardSize; c++) {
        const color = board[r][c];
        if (color === null) continue;

        const xCoord = getCoord(c);
        const yCoord = getCoord(r);
        const isDead = deadStones.has(`${r},${c}`);
        
        ctx.save();
        
        // Faint shadow under stone
        ctx.shadowColor = 'rgba(0, 0, 0, 0.45)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 1.5;
        ctx.shadowOffsetY = 2;

        if (isDead) {
          ctx.globalAlpha = 0.35; // Faded dead stones
        }

        // Draw stone base
        ctx.beginPath();
        ctx.arc(xCoord, yCoord, stoneRadius, 0, Math.PI * 2);

        // Radial gradient for 3D shell/slate stone effect
        const grad = ctx.createRadialGradient(
          xCoord - stoneRadius * 0.2,
          yCoord - stoneRadius * 0.2,
          stoneRadius * 0.1,
          xCoord,
          yCoord,
          stoneRadius
        );

        if (color === 'B') {
          // Black Stone: Glossy slate look
          grad.addColorStop(0, '#4b5563');
          grad.addColorStop(0.3, '#1f2937');
          grad.addColorStop(1, '#090d16');
          ctx.fillStyle = grad;
          ctx.fill();

          // Subtle ring highlights
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        } else {
          // White Stone: Shiny marble look
          grad.addColorStop(0, '#ffffff');
          grad.addColorStop(0.6, '#f3f4f6');
          grad.addColorStop(1, '#d1d5db');
          ctx.fillStyle = grad;
          ctx.fill();

          // Smooth border
          ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }

        ctx.restore();

        // Highlight Last Move
        if (lastMove && lastMove.x === r && lastMove.y === c && !scoringMode) {
          ctx.beginPath();
          ctx.arc(xCoord, yCoord, stoneRadius * 0.35, 0, Math.PI * 2);
          ctx.strokeStyle = color === 'B' ? '#ffffff' : '#111827';
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }
    }

    // 7. Draw Translucent Hover Preview Stone
    if (
      !scoringMode &&
      interactive &&
      !isPending &&
      hoverPt &&
      board[hoverPt.x][hoverPt.y] === null
    ) {
      const hoverX = getCoord(hoverPt.y);
      const hoverY = getCoord(hoverPt.x);
      
      ctx.save();
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.arc(hoverX, hoverY, stoneRadius, 0, Math.PI * 2);

      if (turn === 'B') {
        ctx.fillStyle = '#111827';
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.4)';
        ctx.stroke();
      } else {
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.4)';
        ctx.stroke();
      }
      ctx.restore();
    }

  }, [board, boardSize, lastMove, hoverPt, turn, scoringMode, deadStones, blackTerritory, whiteTerritory, isPending, interactive]);

  // Handle canvas mouse move to calculate grid index for hover
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (scoringMode || !interactive || isPending) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const size = 560;
    const padding = 32;
    const gridArea = size - padding * 2;
    const step = gridArea / (boardSize - 1);

    // Calculate nearest intersection
    const colIdx = Math.round((x - padding) / step);
    const rowIdx = Math.round((y - padding) / step);

    if (rowIdx >= 0 && rowIdx < boardSize && colIdx >= 0 && colIdx < boardSize) {
      // Check if distance to intersection is small enough
      const targetX = padding + colIdx * step;
      const targetY = padding + rowIdx * step;
      const dist = Math.hypot(x - targetX, y - targetY);
      
      if (dist < step * 0.45) {
        setHoverPt({ x: rowIdx, y: colIdx });
      } else {
        setHoverPt(null);
      }
    } else {
      setHoverPt(null);
    }
  };

  const handleMouseLeave = () => {
    setHoverPt(null);
  };

  // Convert mouse clicks to Go board moves
  const handleMouseClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPending) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const size = 560;
    const padding = 32;
    const gridArea = size - padding * 2;
    const step = gridArea / (boardSize - 1);

    const colIdx = Math.round((x - padding) / step);
    const rowIdx = Math.round((y - padding) / step);

    if (rowIdx >= 0 && rowIdx < boardSize && colIdx >= 0 && colIdx < boardSize) {
      const targetX = padding + colIdx * step;
      const targetY = padding + rowIdx * step;
      const dist = Math.hypot(x - targetX, y - targetY);

      if (dist < step * 0.45) {
        if (scoringMode) {
          // In scoring mode, click to toggle dead/alive stones
          if (board[rowIdx][colIdx] !== null) {
            onToggleDeadStone(rowIdx, colIdx);
          }
        } else if (interactive) {
          onPlayMove(rowIdx, colIdx);
        }
      }
    }
  };

  return (
    <div className="canvas-board-wrapper">
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleMouseClick}
        style={{ display: 'block' }}
      />
    </div>
  );
};
