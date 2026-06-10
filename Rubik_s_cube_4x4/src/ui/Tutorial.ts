import { SolveStep } from '../solver/Solver.js';
import { MoveCode } from '../cube/Moves.js';

export type StepCallback = (stepIndex: number, move: MoveCode, moveIndex: number) => void;

export class TutorialPlayer {
  private steps: SolveStep[] = [];
  private flatMoves: { move: MoveCode; stepIndex: number }[] = [];
  private cursor = 0;
  private playing = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private speed = 400; // ms per move
  private onStep: StepCallback;
  private onDone: () => void;
  private onStepChange: (stepIndex: number) => void;

  constructor(
    onStep: StepCallback,
    onDone: () => void,
    onStepChange: (stepIndex: number) => void
  ) {
    this.onStep = onStep;
    this.onDone = onDone;
    this.onStepChange = onStepChange;
  }

  load(steps: SolveStep[]): void {
    this.steps = steps;
    this.flatMoves = [];
    steps.forEach((step, si) => {
      step.moves.forEach(m => this.flatMoves.push({ move: m, stepIndex: si }));
    });
    this.cursor = 0;
    this.playing = false;
  }

  play(): void {
    this.playing = true;
    this.tick();
  }

  pause(): void {
    this.playing = false;
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
  }

  setSpeed(ms: number): void {
    this.speed = ms;
  }

  isPlaying(): boolean { return this.playing; }
  isDone(): boolean { return this.cursor >= this.flatMoves.length; }

  private tick(): void {
    if (!this.playing || this.cursor >= this.flatMoves.length) {
      this.playing = false;
      if (this.cursor >= this.flatMoves.length) this.onDone();
      return;
    }
    const { move, stepIndex } = this.flatMoves[this.cursor];
    this.onStep(stepIndex, move, this.cursor);
    this.onStepChange(stepIndex);
    this.cursor++;
    this.timer = setTimeout(() => this.tick(), this.speed);
  }

  reset(): void {
    this.pause();
    this.cursor = 0;
  }

  getAllMoves(): MoveCode[] {
    return this.flatMoves.map(f => f.move);
  }

  getSteps(): SolveStep[] {
    return this.steps;
  }
}
