import type { Maze, Point } from './mazeGenerator';

// A* Node representation
class Node {
    position: Point;
    g: number;
    h: number;
    parent: Node | null;

    constructor(
        position: Point,
        g: number = 0, // Cost from start
        h: number = 0, // Heuristic cost to end
        parent: Node | null = null
    ) {
        this.position = position;
        this.g = g;
        this.h = h;
        this.parent = parent;
    }

    get f() {
        return this.g + this.h;
    }
}

export function heuristic(a: Point, b: Point): number {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

export function findPathAStar(grid: Maze, start: Point, end: Point): Point[] {
    const openList: Node[] = [];
    const closedList: Node[] = [];

    const startNode = new Node(start);
    openList.push(startNode);

    while (openList.length > 0) {
        // Get the node with minimum f cost
        let currentIndex = 0;
        for (let i = 1; i < openList.length; i++) {
            if (openList[i].f < openList[currentIndex].f) {
                currentIndex = i;
            }
        }

        let currentNode = openList[currentIndex];
        openList.splice(currentIndex, 1);
        closedList.push(currentNode);

        // Found the goal
        if (currentNode.position.x === end.x && currentNode.position.y === end.y) {
            const path: Point[] = [];
            let current: Node | null = currentNode;
            while (current !== null) {
                path.push(current.position);
                current = current.parent;
            }
            return path.reverse();
        }

        // Generate neighbors (up, down, left, right)
        const neighbors = [
            { x: 0, y: -1 },
            { x: 0, y: 1 },
            { x: -1, y: 0 },
            { x: 1, y: 0 }
        ];

        for (const offset of neighbors) {
            const neighborPos = { x: currentNode.position.x + offset.x, y: currentNode.position.y + offset.y };

            // Bounds check
            if (neighborPos.y < 0 || neighborPos.y >= grid.length || neighborPos.x < 0 || neighborPos.x >= grid[0].length) {
                continue;
            }

            // Wall check
            if (grid[neighborPos.y][neighborPos.x] === 1) {
                continue;
            }

            // Check if in closedList
            if (closedList.find(node => node.position.x === neighborPos.x && node.position.y === neighborPos.y)) {
                continue;
            }

            const gScore = currentNode.g + 1;
            const hScore = heuristic(neighborPos, end);

            const existingNode = openList.find(node => node.position.x === neighborPos.x && node.position.y === neighborPos.y);

            if (existingNode) {
                if (gScore < existingNode.g) {
                    existingNode.g = gScore;
                    existingNode.parent = currentNode;
                }
            } else {
                const newNode = new Node(neighborPos, gScore, hScore, currentNode);
                openList.push(newNode);
            }
        }
    }

    return []; // No path found
}
