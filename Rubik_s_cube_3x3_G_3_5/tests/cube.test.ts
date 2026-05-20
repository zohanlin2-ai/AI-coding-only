import { describe, it, expect } from 'vitest';
import { RubiksCube, Move } from '../src/cubeState';
import { solveCube } from '../src/solver';

describe("Rubik's Cube State & Solver Tests", () => {
  it("should initialize as solved", () => {
    const cube = new RubiksCube();
    expect(cube.isSolved()).toBe(true);
  });

  it("should return to solved state after opposite rotations", () => {
    const cube = new RubiksCube();
    cube.move("R");
    expect(cube.isSolved()).toBe(false);
    cube.move("R'");
    expect(cube.isSolved()).toBe(true);

    cube.move("U");
    cube.move("F");
    expect(cube.isSolved()).toBe(false);
    cube.move("F'");
    cube.move("U'");
    expect(cube.isSolved()).toBe(true);
  });

  it("should solve a scrambled cube (20 scrambles)", () => {
    const cube = new RubiksCube();
    const scramble = cube.scramble(20);
    expect(cube.isSolved()).toBe(false);

    // Solve it
    const solution = solveCube(cube);
    
    // Apply solution to the scrambled cube
    solution.forEach(m => cube.move(m));
    
    // It must be solved now
    expect(cube.isSolved()).toBe(true);
  });

  it("should solve a 20-move scramble 100 times to ensure robustness", () => {
    for (let i = 0; i < 100; i++) {
      const cube = new RubiksCube();
      cube.scramble(20);
      expect(cube.isSolved()).toBe(false);

      const solution = solveCube(cube);
      solution.forEach(m => cube.move(m));

      expect(cube.isSolved()).toBe(true);
    }
  });
});
