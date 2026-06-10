import { CubeState } from './cube/State.js';
import { applyMove, scramble, MoveCode } from './cube/Moves.js';
import { solve } from './solver/Solver.js';
import { Renderer } from './ui/Renderer.js';
import { TutorialPlayer } from './ui/Tutorial.js';

let state = new CubeState();
let moveCount = 0;
let currentStepIndex = -1;

const container = document.getElementById('canvas-container')!;
const renderer = new Renderer(container);
renderer.updateState(state);

const statusBox = document.getElementById('status-box')!;
const moveDisplay = document.getElementById('move-display')!;
const moveCountEl = document.getElementById('move-count')!;
const btnScramble = document.getElementById('btn-scramble')!;
const btnSolve = document.getElementById('btn-solve')!;
const btnReset = document.getElementById('btn-reset')!;
const btnPause = document.getElementById('btn-pause')!;
const speedSlider = document.getElementById('speed-slider') as HTMLInputElement;

function setStatus(msg: string): void {
  statusBox.innerHTML = msg;
}

function updateStepHighlight(stepIndex: number): void {
  if (stepIndex === currentStepIndex) return;
  currentStepIndex = stepIndex;
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (!el) continue;
    el.className = 'step' + (i < stepIndex ? ' done' : i === stepIndex ? ' active' : '');
  }
  renderer.highlightStep(stepIndex);
}

const player = new TutorialPlayer(
  (stepIndex, move) => {
    state = applyMove(state, move as MoveCode);
    renderer.updateState(state);
    moveCount++;
    moveCountEl.textContent = `Moves: ${moveCount}`;
    updateStepHighlight(stepIndex);
  },
  () => {
    setStatus(state.isSolved()
      ? '✓ Solved! All steps complete.'
      : 'Steps complete. Small deviations may remain (heuristic solver).');
    btnPause.style.display = 'none';
    btnSolve.style.display = '';
    for (let i = 0; i < 4; i++) {
      const el = document.getElementById(`step-${i}`);
      if (el) el.className = 'step done';
    }
  },
  updateStepHighlight
);

btnScramble.addEventListener('click', () => {
  player.reset();
  const result = scramble(new CubeState(), 40);
  state = result.state;
  moveCount = 0;
  moveCountEl.textContent = 'Moves: 0';
  renderer.updateState(state);
  moveDisplay.textContent = result.moves.join(' ');
  setStatus('Scrambled! Click Solve to see the solution.');
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) el.className = 'step';
  }
  currentStepIndex = -1;
  btnPause.style.display = 'none';
  btnSolve.style.display = '';
});

btnSolve.addEventListener('click', () => {
  if (state.isSolved()) {
    setStatus('Already solved!');
    return;
  }
  const steps = solve(state);
  player.load(steps);
  const allMoves = player.getAllMoves();
  moveDisplay.textContent = allMoves.join(' ') || '(no moves needed)';
  setStatus(`Solving... ${allMoves.length} moves across ${steps.length} stages.`);
  btnPause.style.display = '';
  btnSolve.style.display = 'none';
  player.play();
});

btnPause.addEventListener('click', () => {
  if (player.isPlaying()) {
    player.pause();
    btnPause.textContent = 'Resume';
    setStatus('Paused. Click Resume to continue.');
  } else {
    player.play();
    btnPause.textContent = 'Pause';
    setStatus('Resuming...');
  }
});

btnReset.addEventListener('click', () => {
  player.reset();
  state = new CubeState();
  moveCount = 0;
  moveCountEl.textContent = 'Moves: 0';
  renderer.updateState(state);
  moveDisplay.textContent = '—';
  setStatus('Reset to solved state.');
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) el.className = 'step';
  }
  currentStepIndex = -1;
  btnPause.style.display = 'none';
  btnSolve.style.display = '';
  btnPause.textContent = 'Pause';
});

speedSlider.addEventListener('input', () => {
  // slider max=800 is slow, min=100 is fast — invert
  const ms = 900 - parseInt(speedSlider.value);
  player.setSpeed(ms);
});
