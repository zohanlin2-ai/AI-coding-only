export type Point = { x: number; y: number };
export type Maze = number[][]; // 0 = path, 1 = wall

// Create a maze using Recursive Backtracking algorithm
export function generateMaze(width: number, height: number): { grid: Maze; start: Point; end: Point } {
    // Ensure dimensions are odd for walls/paths to work correctly
    const w = width % 2 === 0 ? width + 1 : width;
    const h = height % 2 === 0 ? height + 1 : height;

    const grid: Maze = Array.from({ length: h }, () => Array(w).fill(1));
    const start = { x: 1, y: 1 };

    function carvePassagesFrom(cx: number, cy: number) {
        const directions = [
            { dx: 0, dy: -2 }, // Up
            { dx: 0, dy: 2 },  // Down
            { dx: 2, dy: 0 },  // Right
            { dx: -2, dy: 0 }  // Left
        ];

        // Shuffle directions
        directions.sort(() => Math.random() - 0.5);

        for (const { dx, dy } of directions) {
            const nx = cx + dx;
            const ny = cy + dy;

            if (ny > 0 && ny < h - 1 && nx > 0 && nx < w - 1 && grid[ny][nx] === 1) {
                grid[cy + dy / 2][cx + dx / 2] = 0; // Carve through the wall
                grid[ny][nx] = 0;                  // Carve the cell
                carvePassagesFrom(nx, ny);
            }
        }
    }

    grid[start.y][start.x] = 0;
    carvePassagesFrom(start.x, start.y);

    // Find a suitable end point at the bottom right
    let end = { x: w - 2, y: h - 2 };
    if (grid[end.y][end.x] === 1) {
        // If blocked, search for nearest free cell
        outer: for (let y = h - 2; y > 0; y--) {
            for (let x = w - 2; x > 0; x--) {
                if (grid[y][x] === 0) {
                    end = { x, y };
                    break outer;
                }
            }
        }
    }

    return { grid, start, end };
}
