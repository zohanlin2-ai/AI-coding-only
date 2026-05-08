import React from 'react';
import type { Point, Maze } from '../utils/mazeGenerator';
import { Mouse as MouseIcon } from 'lucide-react';

interface MazeGridProps {
    grid: Maze;
    mousePos: Point;
    cheesePos: Point;
    path: Point[];
    footprints: Point[];
}

const MazeGrid: React.FC<MazeGridProps> = ({ grid, mousePos, cheesePos, path, footprints }) => {
    if (!grid || grid.length === 0) return null;

    const rows = grid.length;
    const cols = grid[0].length;

    return (
        <div
            className="maze-grid"
            style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${cols}, 1fr)`,
                gridTemplateRows: `repeat(${rows}, 1fr)`,
                position: 'relative'
            }}
        >
            {grid.map((row, y) => (
                row.map((cell, x) => {
                    const isWall = cell === 1;
                    const isCheese = cheesePos.x === x && cheesePos.y === y;
                    const isPath = path.some(p => p.x === x && p.y === y);
                    const isFootprint = footprints.some(p => p.x === x && p.y === y);

                    let cellClass = 'cell ';
                    if (isWall) cellClass += 'wall ';
                    else cellClass += 'path ';

                    if (isFootprint) cellClass += 'footprint ';
                    if (isPath && !isCheese && !isFootprint) cellClass += 'highlighted-path ';

                    return (
                        <div key={`${x}-${y}`} className={cellClass}>
                            {isCheese && <span className="cheese" title="Cheese">🧀</span>}
                        </div>
                    );
                })
            ))}

            {/* Absolutely positioned mouse for smooth animations */}
            <div
                className="mouse-container"
                style={{
                    left: `${(mousePos.x / cols) * 100}%`,
                    top: `${(mousePos.y / rows) * 100}%`,
                    width: `${(1 / cols) * 100}%`,
                    height: `${(1 / rows) * 100}%`
                }}
            >
                <MouseIcon size={24} className="mouse-icon" />
            </div>
        </div>
    );
};

export default MazeGrid;
