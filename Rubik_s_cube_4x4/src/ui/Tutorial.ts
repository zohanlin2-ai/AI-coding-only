import { SolveStep } from '../solver/Solver.js';
import { MoveCode } from '../cube/Moves.js';

// Plays a move and resolves when its turn animation finishes.
export type PlayMove = (stepIndex: number, move: MoveCode, moveIndex: number) => Promise<void>;

export class TutorialPlayer {
  private steps: SolveStep[] = [];
  private flatMoves: { move: MoveCode; stepIndex: number }[] = [];
  private cursor = 0;
  private playing = false;
  private playMove: PlayMove;
  private onDone: () => void;
  private onStepChange: (stepIndex: number) => void;

  constructor(
    playMove: PlayMove,
    onDone: () => void,
    onStepChange: (stepIndex: number) => void
  ) {
    this.playMove = playMove;
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
    if (this.playing) return;
    this.playing = true;
    void this.run();
  }

  pause(): void {
    this.playing = false;
  }

  isPlaying(): boolean { return this.playing; }
  isDone(): boolean { return this.cursor >= this.flatMoves.length; }

  private async run(): Promise<void> {
    while (this.playing && this.cursor < this.flatMoves.length) {
      const { move, stepIndex } = this.flatMoves[this.cursor];
      this.onStepChange(stepIndex);
      await this.playMove(stepIndex, move, this.cursor);
      this.cursor++;
    }
    if (this.cursor >= this.flatMoves.length) {
      this.playing = false;
      this.onDone();
    }
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
