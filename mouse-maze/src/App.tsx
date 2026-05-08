import { useState, useEffect } from 'react';
import './App.css';
import MazeGrid from './components/MazeGrid';
import Controls from './components/Controls';
import { generateMaze } from './utils/mazeGenerator';
import type { Maze, Point } from './utils/mazeGenerator';
import { findPathAStar } from './utils/pathfinding';

function App() {
  const [grid, setGrid] = useState<Maze>([]);
  const [cheesePos, setCheesePos] = useState<Point>({ x: 1, y: 1 });
  const [mousePos, setMousePos] = useState<Point>({ x: 1, y: 1 });

  const [path, setPath] = useState<Point[]>([]);
  const [footprints, setFootprints] = useState<Point[]>([]);
  const [isNavigating, setIsNavigating] = useState(false);

  // Initialize maze
  useEffect(() => {
    handleGenerateMaze();
  }, []);

  const handleGenerateMaze = () => {
    const { grid: newGrid, start, end } = generateMaze(21, 21); // 21x21 grid
    setGrid(newGrid);
    setCheesePos(end);
    setMousePos(start);
    setPath([]);
    setFootprints([]);
    setIsNavigating(false);
  };

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const handleStartNavigation = async () => {
    if (isNavigating) return;

    // Find path using A*
    const calculatedPath = findPathAStar(grid, mousePos, cheesePos);

    if (calculatedPath.length === 0) {
      alert("找不到路徑！(No path found)");
      return;
    }

    setPath(calculatedPath);
    setIsNavigating(true);

    // Animate mouse movement
    for (let i = 0; i < calculatedPath.length; i++) {
      const step = calculatedPath[i];

      setMousePos(prevMouse => {
        // Before moving to next cell, add current to footprints
        setFootprints(prev => [...prev, prevMouse]);
        return step;
      });

      await delay(150); // Animation speed
    }

    setIsNavigating(false); // Done
  };

  return (
    <div className="app-container">
      <header className="header glassmorphism">
        <h1>老鼠走迷宮 (Mouse Maze)</h1>
        <p>A* Pathfinding Visualization</p>
      </header>

      <main className="main-content">
        <div className="maze-wrapper">
          <MazeGrid
            grid={grid}
            mousePos={mousePos}
            cheesePos={cheesePos}
            path={path}
            footprints={footprints}
          />
        </div>
        <Controls
          onGenerate={handleGenerateMaze}
          onStart={handleStartNavigation}
          isNavigating={isNavigating}
        />
      </main>
    </div>
  );
}

export default App;
