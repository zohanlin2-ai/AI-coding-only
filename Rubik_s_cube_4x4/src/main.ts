import { CubeState } from './cube/State.js';
import { applyMove, scramble, MoveCode } from './cube/Moves.js';
import { solve } from './solver/Solver.js';
import { Renderer } from './ui/Renderer.js';
import { TutorialPlayer } from './ui/Tutorial.js';

let state = new CubeState();
let moveCount = 0;
let currentStepIndex = -1;
let turnDuration = 500; // ms per turn, controlled live by the speed slider
let runId = 0; // bumped to abort an in-flight scramble/solve

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

function setMoveCount(n: number): void {
  moveCount = n;
  moveCountEl.textContent = `Moves: ${moveCount}`;
}

function resetStepHighlights(): void {
  currentStepIndex = -1;
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) el.className = 'step';
  }
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
  async (stepIndex, move) => {
    state = applyMove(state, move as MoveCode);
    await renderer.animateMove(move as MoveCode, state, turnDuration);
    setMoveCount(moveCount + 1);
    updateStepHighlight(stepIndex);
  },
  () => {
    setStatus(state.isSolved()
      ? '✓ Solved! All steps complete.'
      : 'Steps complete.');
    btnPause.style.display = 'none';
    btnSolve.style.display = '';
    for (let i = 0; i < 4; i++) {
      const el = document.getElementById(`step-${i}`);
      if (el) el.className = 'step done';
    }
  },
  updateStepHighlight
);

btnScramble.addEventListener('click', async () => {
  player.reset();
  const myRun = ++runId;
  const result = scramble(new CubeState(), 40);
  const target = result.state;

  setMoveCount(0);
  setStatus('Scrambling...');
  moveDisplay.textContent = result.moves.join(' ');
  resetStepHighlights();
  btnPause.style.display = 'none';
  btnSolve.style.display = '';

  // Animate the scramble move-by-move, starting from a solved cube.
  state = new CubeState();
  renderer.updateState(state);
  for (const m of result.moves) {
    if (myRun !== runId) return; // aborted by another action
    state = applyMove(state, m);
    await renderer.animateMove(m, state, turnDuration);
    setMoveCount(moveCount + 1);
  }
  state = target;
  setStatus('Scrambled! Click Solve to see the solution.');
});

btnSolve.addEventListener('click', () => {
  if (renderer.isAnimating() || player.isPlaying()) return;
  if (state.isSolved()) {
    setStatus('Already solved!');
    return;
  }
  ++runId; // claim control away from any scramble loop
  const steps = solve(state);
  player.load(steps);
  const allMoves = player.getAllMoves();
  moveDisplay.textContent = allMoves.join(' ') || '(no moves needed)';
  setStatus(`Solving... ${allMoves.length} moves across ${steps.length} stages.`);
  setMoveCount(0);
  btnPause.style.display = '';
  btnPause.textContent = 'Pause';
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
  ++runId; // abort any running scramble/solve
  player.reset();
  state = new CubeState();
  setMoveCount(0);
  renderer.updateState(state);
  moveDisplay.textContent = '—';
  setStatus('Reset to solved state.');
  resetStepHighlights();
  btnPause.style.display = 'none';
  btnSolve.style.display = '';
  btnPause.textContent = 'Pause';
});

speedSlider.addEventListener('input', () => {
  // slider: higher value = faster turn = shorter duration (live)
  turnDuration = 900 - parseInt(speedSlider.value);
});
turnDuration = 900 - parseInt(speedSlider.value);
