# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2026-05-20

### Fixed
- **Face Color Lag & Instant-Stop Flash**: Fixed a visual bug where stopping a turn animation (such as `L`) caused the color on the newly rotated face (e.g., U or F faces) to flash/display the old face's color before restoring. This was caused by the CSS rule `transition: background-color 0.2s ease` on the sticker elements, which delayed the color updates. Removing this transition ensures that the colors update instantly on the exact same frame as the 3D transform reset, achieving 100% seamless, flash-free face rotations.

## [1.0.4] - 2026-05-20

### Fixed
- **3D Z-Fighting & Face Flickering**: Fixed a rendering issue where rotating any face caused some cubie surfaces to flicker. This was caused by `backface-visibility: visible` and semi-transparent borders (`rgba(...)`) on `.face` elements, forcing the browser's graphics engine to perform expensive alpha-blending depth calculations on back-facing polygons. Resolved by setting `backface-visibility: hidden` and converting the border to a solid, opaque black (`#000000`), completely eliminating Z-fighting and flickering.

## [1.0.3] - 2026-05-20

### Fixed
- **Off-Center Rotation & Layer Wobble**: Fixed a critical 3D layout bug where `.cubie` elements were positioned without centering offsets, causing their local coordinate origins to reside at the top-left corner instead of their center. During face turn animations, this offset caused the rotating layer to orbit eccentrically (wobble) and physically jump/snap by up to 60px when the animation finished, making colors look scrambled or altered. Centered `.cubie` on the translated origin by adding CSS offset translations, ensuring perfectly concentric rotation and zero visual snapping.

## [1.0.2] - 2026-05-20

### Added
- **Premium Solid Black Cube Body & Spacing**: Restructured the 3D Cubie Face CSS design. Each cubie face is now a solid full-size black container (representing a real plastic body), and the colored stickers are rendered using `::after` pseudo-elements. This blocks the viewport from seeing through the cube's interior to the blue background, making all gaps and spaces between the small cubies solid, deep black.
- **Canary Yellow Color Brightening**: Brightened the Yellow face color from gold/mustard `#eab308` to a vibrant canary yellow `#ffea00` for high contrast and premium glow.

## [1.0.1] - 2026-05-20

### Fixed
- **Scramble Concurrency Synchronization Bug**: Fixed a bug where clicking the Scramble button instantly updated the logical state of the cube, causing the subsequent visual move animations to render using already scrambled colors (giving the appearance of corrupted or altered colors). Scramble moves are now pushed to the queue to execute sequentially, ensuring the colors and positions are perfectly synchronized at every step of the animation.
- **R/L Face Animation Angle Mismatches**: Corrected the visual rotation angles for `R`, `R'`, `L`, and `L'` moves in the CSS animation definitions. Previously, the visual animations for these faces rotated in the opposite direction of the logical state updates, causing the colors on the faces to jump/snap instantly at the end of the turn animation (which looked like colors being altered or tampered). Now, all 3D turns flow continuously and accurately matching their logical state transitions.

## [1.0.0] - 2026-05-20

### Added
- **Interactive 3D Rubik's Cube Simulator**: Fully responsive 3D Web UI built with HTML5, CSS 3D transforms, and TypeScript.
- **Layer-By-Layer (LBL) Solver Algorithm**: Self-developed full 3x3 Rubik's Cube solver logic implementing:
  - Phase 1: White Cross
  - Phase 2: White Corners (First Layer)
  - Phase 3: Middle Layer Edges (Second Layer)
  - Phase 4: Orientation of Last Layer (OLL) using BFS solver with `K_MOVE` and `S_MOVE` macros
  - Phase 5: Permutation of Last Layer (PLL) using BFS solver with `P_MOVE` and `U_PERM` macros
- **Solver Playback Dashboard**: High-fidelity controls featuring:
  - Play, Pause, Next Step, Previous Step (Undoing moves using inverse rotations!)
  - Interactive speed slider (100ms - 1000ms animation duration)
  - Real-time step progress badge (Ready / Solving / Solved!)
  - Visual timeline displaying computed solver moves stream with live highlights
- **Robustness Test Suite**: Comprehensive unit tests (Vitest) validating:
  - Cube rotation logic correctness
  - Randomly scrambled state solving (100 sequential full solver loops)
  - Edge and corner tracking robustness
- **Interactive Viewport Control**: Drag and touch events supporting full 3D camera rotation around the cube.
- **Documentation**: Comprehensive `README.md` detailing architecture, commands, and developer guide.

### Changed
- Refactored Vite boilerplate code to render premium Rubik's Cube application.
- Simplified solver state space representations using stateless coordinate-based lookups for OLL and PLL BFS solvers, ensuring high performance.

### Fixed
- Fixed White Cross edge insertion and kickout logical bugs that previously caused infinite loops.
- Corrected PLL and OLL BFS state representation mismatches.
- Resolved type import syntax issues under TypeScript verbatimModuleSyntax configuration.
