# 3D 3x3 Rubik's Cube Simulator & LBL Solver

An interactive 3D Rubik's Cube Simulator and Layer-By-Layer (LBL) Auto-Solver built with **TypeScript**, HTML5, and Vanilla CSS 3D transforms. 

This project follows the strict development guidelines inspired by Andrej Karpathy, featuring modularity, zero third-party visual dependency, and a comprehensive test-driven design.

## 🚀 Features

- **Premium 3D Visualizer**: Pure CSS 3D transforms rendering of a realistic Rubik's Cube, including realistic sticker borders, spacing, and glowing HSL color palettes.
- **Interactive Controls**:
  - **Click-and-Drag**: Rotate the viewport camera 360° to view the cube from any angle.
  - **Manual Rotations**: Access basic face turn buttons (`U`, `D`, `F`, `B`, `L`, `R` and their counter-clockwise inverse primes).
  - **Random Scramble**: Generate a standard random 20-move scramble sequence.
  - **Force Reset**: Instantly restore the cube state to solved with a premium fade transition.
- **LBL Solver Dashboard**:
  - **Auto Solve**: Computes the optimal LBL moves list.
  - **Playback Controller**: Play, pause, step forward, or **step backward** (rewinds moves using inverse rotations!).
  - **Speed Slider**: Real-time speed adjustment (100ms - 1000ms per turn).
  - **Moves Stream**: Interactive timeline showing all solution moves, highlighting the active one.
- **100% Correct Solver**: Backed by a Vitest suite running 100 random 20-move scrambles phase-by-phase.

---

## 🛠️ Technology Stack & Development Language

- **Logic & Algorithm**: **TypeScript (v5.6.3)**
  - Self-developed coordinate-based permutation logic.
  - Strict type checking and verbatim syntax compliance.
- **UI & Rendering**: **HTML5 & Vanilla CSS 3D Transforms**
  - Smooth animation easing using cubic Bezier transforms.
  - Zero heavy 3D engine dependencies (no three.js), resulting in a lightning-fast build and load time.
- **Build System**: **Vite (v6.0.11)**
- **Testing**: **Vitest (v4.1.6)**

---

## 📖 LBL Solver Algorithm Architecture

The solver is divided into 5 phases in [solver.ts](file:///C:/Users/zohan/.gemini/antigravity/scratch/Rubik_s_cube_3x3_G_3_5/src/solver.ts):

1. **White Cross (Phase 1)**: Matches the 4 white edge pieces (`U-F`, `U-R`, `U-B`, `U-L`) to their respective side centers while keeping the white face on the `U` layer.
2. **White Corners (Phase 2)**: Places the 4 corner pieces (`U-F-R`, `U-F-L`, `U-B-R`, `U-B-L`) to their slots, completing the first layer.
3. **Middle Edges (Phase 3)**: Solves the middle layer edge pieces (`F-R`, `F-L`, `B-R`, `B-L`) using left/right insert algorithms, completing the first two layers (F2L).
4. **Orientation of Last Layer - OLL (Phase 4)**: Orients the bottom `D` face (Yellow) using a Breadth-First Search (BFS) solver utilizing:
  - `K_MOVE` (edge orientation macro): `F' R' D' R D F`
  - `S_MOVE` (corner orientation / Sune macro): `R D R' D R D2 R'`
5. **Permutation of Last Layer - PLL (Phase 5)**: Permutes the bottom layer edge and corner pieces into their final positions using a BFS solver utilizing:
  - `P_MOVE` (corner permutation macro): `R F' R B2 R' F R B2 R2`
  - `U_PERM` (edge permutation macro): `R2 D R D R' D' R' D' R' D R'`

---

## 💻 Commands

### Installation
Install the project dependencies:
```bash
npm install
```

### Run Locally (Development Server)
Launch the local developer server:
```bash
npm run dev
```

### Build & Package (Production)
Compile and bundle the project:
```bash
npm run build
```

### Run Unit Tests
Execute the Vitest test suites (runs the 100-scramble solver robustness tests):
```bash
npm run test
```

---

## 📂 File Structure

```
├── .cursor/               # Cursor configurations and rules
├── src/
│   ├── assets/            # App visual assets (SVG logos)
│   ├── cubeState.ts       # Cube state class, coordinate system, and move rotations
│   ├── solver.ts          # LBL solver algorithm and state search helpers
│   ├── main.ts            # UI Event controller, animation loops, and playback logic
│   └── style.css          # Premium Dark UI style sheet with 3D viewport configs
├── tests/
│   └── cube.test.ts       # Unit tests & 100-scramble robustness verification
├── index.html             # UI layout and metadata headers
├── package.json           # Scripts and dependencies
└── tsconfig.json          # TypeScript build parameters
```

## ⚖️ License
This project is open-source and available under the MIT License.
