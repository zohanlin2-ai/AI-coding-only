import './style.css';
import { RubiksCube } from './cubeState';
import type { Move } from './cubeState';
import { solveCube } from './solver';

// Initialize core cube state
const cube = new RubiksCube();

// CSS rotation definitions for each move
const MOVE_ANIMS: Record<Move, { axis: 'X' | 'Y' | 'Z'; angle: number; filter: (c: any) => boolean }> = {
  'R':  { axis: 'X', angle: 90,  filter: c => c.x === 1 },
  "R'": { axis: 'X', angle: -90, filter: c => c.x === 1 },
  'L':  { axis: 'X', angle: -90, filter: c => c.x === -1 },
  "L'": { axis: 'X', angle: 90,  filter: c => c.x === -1 },
  'U':  { axis: 'Y', angle: -90, filter: c => c.y === 1 },
  "U'": { axis: 'Y', angle: 90,  filter: c => c.y === 1 },
  'D':  { axis: 'Y', angle: 90,  filter: c => c.y === -1 },
  "D'": { axis: 'Y', angle: -90, filter: c => c.y === -1 },
  'F':  { axis: 'Z', angle: 90,  filter: c => c.z === 1 },
  "F'": { axis: 'Z', angle: -90, filter: c => c.z === 1 },
  'B':  { axis: 'Z', angle: -90, filter: c => c.z === -1 },
  "B'": { axis: 'Z', angle: 90,  filter: c => c.z === -1 }
};

// Animation state
let activeMove: Move | null = null;
let animMoveInfo: typeof MOVE_ANIMS[Move] | null = null;
let currentAnimAngle = 0;
let animStartTime = 0;
let animDuration = 300; // ms (adjustable via slider)

// Queue of moves to execute sequentially
let moveQueue: Move[] = [];

// Solver / Playback state
let isPlaying = false;
let solutionMoves: Move[] = [];
let currentStepIdx = 0;

// Camera view state
let rotX = -30;
let rotY = 45;
let isDragging = false;
let startX = 0;
let startY = 0;

// DOM Elements
const container = document.getElementById('cube-container')!;
const scene = document.getElementById('scene')!;
const playbackPanel = document.getElementById('playback-panel')!;
const btnScramble = document.getElementById('btn-scramble')!;
const btnSolve = document.getElementById('btn-solve')!;
const btnReset = document.getElementById('btn-reset')!;
const btnPlayPause = document.getElementById('btn-play-pause')! as HTMLButtonElement;
const btnPrev = document.getElementById('btn-prev')! as HTMLButtonElement;
const btnNext = document.getElementById('btn-next')! as HTMLButtonElement;
const speedSlider = document.getElementById('speed-slider')! as HTMLInputElement;
const speedVal = document.getElementById('speed-val')!;
const movesStream = document.getElementById('moves-stream')!;
const progressText = document.getElementById('solve-progress')!;
const statusBadge = document.getElementById('solve-status-badge')!;

// 1. Initial cubies DOM generation & positioning
function initCubeRender() {
  container.innerHTML = '';
  for (let i = 0; i < 27; i++) {
    const cubieDiv = document.createElement('div');
    cubieDiv.className = 'cubie';
    
    // Create 6 faces
    ['front', 'back', 'up', 'down', 'left', 'right'].forEach(f => {
      const faceDiv = document.createElement('div');
      faceDiv.className = `face ${f}`;
      cubieDiv.appendChild(faceDiv);
    });
    
    container.appendChild(cubieDiv);
  }
}

// 2. Stateless DOM update based on cubeState data
function updateCubeRender() {
  cube.cubies.forEach((c, idx) => {
    const cubieDiv = container.children[idx] as HTMLDivElement;
    if (!cubieDiv) return;

    // Map face classes to cubieState keys
    const faceMappings: Record<string, 'F' | 'B' | 'U' | 'D' | 'L' | 'R'> = {
      'front': 'F',
      'back': 'B',
      'up': 'U',
      'down': 'D',
      'left': 'L',
      'right': 'R'
    };

    // Update face colors
    Object.entries(faceMappings).forEach(([faceClass, faceKey]) => {
      const faceDiv = cubieDiv.querySelector(`.face.${faceClass}`) as HTMLDivElement;
      if (!faceDiv) return;

      faceDiv.className = `face ${faceClass}`; // Reset classes
      const color = c.colors[faceKey];
      if (color) {
        faceDiv.classList.add(color);
      }
    });

    // 3D positioning
    const size = 64; // Spacing size in px
    const tx = c.x * size;
    const ty = -c.y * size; // CSS Y-axis goes down, so invert
    const tz = c.z * size;

    let transform = `translate3d(${tx}px, ${ty}px, ${tz}px)`;

    // Apply active rotation animation if applicable
    if (activeMove && animMoveInfo && animMoveInfo.filter(c)) {
      transform = `rotate${animMoveInfo.axis}(${currentAnimAngle}deg) ` + transform;
    }

    cubieDiv.style.transform = transform;
  });
}

// 3. Viewport Drag Controls
scene.addEventListener('pointerdown', (e: PointerEvent) => {
  isDragging = true;
  startX = e.clientX;
  startY = e.clientY;
  scene.style.cursor = 'grabbing';
});

window.addEventListener('pointermove', (e: PointerEvent) => {
  if (!isDragging) return;
  const dx = e.clientX - startX;
  const dy = e.clientY - startY;

  rotY += dx * 0.4;
  rotX -= dy * 0.4;

  // Clamp vertical rotation to avoid gimbal lock/flip
  rotX = Math.max(-80, Math.min(80, rotX));

  container.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;

  startX = e.clientX;
  startY = e.clientY;
});

window.addEventListener('pointerup', () => {
  isDragging = false;
  scene.style.cursor = 'grab';
});

// Quad easing for premium feel
function easeOutQuad(x: number): number {
  return 1 - (1 - x) * (1 - x);
}

// 4. Main animation loop
function animationLoop(now: number) {
  if (activeMove && animMoveInfo) {
    const elapsed = now - animStartTime;
    const t = Math.min(elapsed / animDuration, 1);
    
    currentAnimAngle = animMoveInfo.angle * easeOutQuad(t);
    updateCubeRender();

    if (t >= 1) {
      // Commit logic change on rotation end
      cube.move(activeMove);
      activeMove = null;
      animMoveInfo = null;
      currentAnimAngle = 0;
      updateCubeRender();
      
      processQueue();
    }
  } else {
    processQueue();
  }
  requestAnimationFrame(animationLoop);
}

function processQueue() {
  if (activeMove) return;
  
  if (moveQueue.length > 0) {
    const m = moveQueue.shift()!;
    activeMove = m;
    animMoveInfo = MOVE_ANIMS[m];
    currentAnimAngle = 0;
    animStartTime = performance.now();
  } else if (isPlaying) {
    // If playing solver and queue is done, run next playback step
    setTimeout(triggerNextPlaybackStep, 50); // slight pause between moves for aesthetics
  }
}

// 5. Playback UI update
function updatePlaybackUI() {
  progressText.innerText = `Step ${currentStepIdx}/${solutionMoves.length}`;
  
  // Highlight active move in stream
  const movesChildren = movesStream.children;
  for (let i = 0; i < movesChildren.length; i++) {
    const child = movesChildren[i] as HTMLDivElement;
    if (i === currentStepIdx) {
      child.classList.add('active');
      child.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    } else {
      child.classList.remove('active');
    }
  }

  // Update badge status
  if (currentStepIdx === 0) {
    statusBadge.innerText = 'Ready';
    statusBadge.style.background = 'rgba(59, 130, 246, 0.15)';
    statusBadge.style.color = '#60a5fa';
  } else if (currentStepIdx < solutionMoves.length) {
    statusBadge.innerText = 'Solving';
    statusBadge.style.background = 'rgba(234, 179, 8, 0.15)';
    statusBadge.style.color = '#facc15';
  } else {
    statusBadge.innerText = 'Solved!';
    statusBadge.style.background = 'rgba(16, 185, 129, 0.15)';
    statusBadge.style.color = '#10b981';
  }
}

function triggerNextPlaybackStep() {
  if (!isPlaying) return;

  if (currentStepIdx < solutionMoves.length) {
    const m = solutionMoves[currentStepIdx];
    updatePlaybackUI();
    moveQueue.push(m);
    currentStepIdx++;
  } else {
    isPlaying = false;
    btnPlayPause.innerText = '▶️ Play';
    updatePlaybackUI();
  }
}

function getInverseMove(m: Move): Move {
  if (m.endsWith("'")) return m.slice(0, -1) as Move;
  return `${m}'` as Move;
}

// 6. Action Listeners
btnScramble.addEventListener('click', () => {
  // Exit solver view
  isPlaying = false;
  playbackPanel.classList.add('hidden');
  moveQueue = [];
  activeMove = null;
  animMoveInfo = null;
  updateCubeRender();
  
  // Generate 20 random moves and queue them to animate and mutate sequentially
  const possibleMoves: Move[] = ['U', "U'", 'D', "D'", 'L', "L'", 'R', "R'", 'F', "F'", 'B', "B'"];
  for (let i = 0; i < 20; i++) {
    const randMove = possibleMoves[Math.floor(Math.random() * possibleMoves.length)];
    moveQueue.push(randMove);
  }
});

btnSolve.addEventListener('click', () => {
  if (cube.isSolved() && moveQueue.length === 0) {
    alert("The cube is already solved!");
    return;
  }
  
  // Exit any previous play state
  isPlaying = false;
  moveQueue = [];
  activeMove = null;
  animMoveInfo = null;
  updateCubeRender();

  // Solve cube from current logical state
  solutionMoves = solveCube(cube);
  currentStepIdx = 0;
  
  // Render moves stream
  movesStream.innerHTML = '';
  solutionMoves.forEach((m, idx) => {
    const item = document.createElement('div');
    item.className = 'stream-move';
    item.innerText = `${idx + 1}. ${m}`;
    movesStream.appendChild(item);
  });

  // Prepare UI
  playbackPanel.classList.remove('hidden');
  isPlaying = true;
  btnPlayPause.innerText = '⏸️ Pause';
  updatePlaybackUI();
});

btnReset.addEventListener('click', () => {
  isPlaying = false;
  moveQueue = [];
  activeMove = null;
  animMoveInfo = null;
  playbackPanel.classList.add('hidden');
  
  // Hard reset logic state
  cube.reset();
  
  // Flash transition styling on cube container
  container.style.transition = 'none';
  container.style.opacity = '0';
  setTimeout(() => {
    updateCubeRender();
    container.style.transition = 'opacity 0.4s ease';
    container.style.opacity = '1';
  }, 50);
});

// Playback Control events
btnPlayPause.addEventListener('click', () => {
  if (currentStepIdx >= solutionMoves.length && !isPlaying) {
    // Reset to start if finished
    currentStepIdx = 0;
  }
  isPlaying = !isPlaying;
  btnPlayPause.innerText = isPlaying ? '⏸️ Pause' : '▶️ Play';
});

btnNext.addEventListener('click', () => {
  isPlaying = false;
  btnPlayPause.innerText = '▶️ Play';
  
  if (currentStepIdx < solutionMoves.length && !activeMove) {
    const m = solutionMoves[currentStepIdx];
    updatePlaybackUI();
    moveQueue.push(m);
    currentStepIdx++;
  }
});

btnPrev.addEventListener('click', () => {
  isPlaying = false;
  btnPlayPause.innerText = '▶️ Play';
  
  if (currentStepIdx > 0 && !activeMove) {
    currentStepIdx--;
    const m = solutionMoves[currentStepIdx];
    const inv = getInverseMove(m);
    moveQueue.push(inv);
    updatePlaybackUI();
  }
});

// Speed slider event
speedSlider.addEventListener('input', (e) => {
  const val = (e.target as HTMLInputElement).value;
  animDuration = parseInt(val);
  speedVal.innerText = val;
});

// Manual rotations buttons
document.querySelectorAll('.btn-manual').forEach(btn => {
  btn.addEventListener('click', (e) => {
    // Pause any playing solver
    if (isPlaying) {
      isPlaying = false;
      btnPlayPause.innerText = '▶️ Play';
    }
    
    const move = (e.target as HTMLButtonElement).dataset.move as Move;
    moveQueue.push(move);
  });
});

// Start app
initCubeRender();
updateCubeRender();
requestAnimationFrame(animationLoop);
scene.style.cursor = 'grab';
container.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;
