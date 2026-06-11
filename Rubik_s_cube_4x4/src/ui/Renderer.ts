import * as THREE from 'three';
import { CubeState, COLOR_HEX } from '../cube/State.js';
import { MoveCode, TURN_INFO } from '../cube/Moves.js';

const CUBIE_SIZE = 0.92;
const GAP = 1.0;
const FACE_OFFSET = 0.462;

// 4x4: cubies at positions -1.5, -0.5, 0.5, 1.5 on each axis
function cubiePositions(): { gx: number; gy: number; gz: number; pos: THREE.Vector3 }[] {
  const out: { gx: number; gy: number; gz: number; pos: THREE.Vector3 }[] = [];
  for (let gx = 0; gx < 4; gx++)
    for (let gy = 0; gy < 4; gy++)
      for (let gz = 0; gz < 4; gz++)
        out.push({ gx, gy, gz, pos: new THREE.Vector3((gx - 1.5) * GAP, (gy - 1.5) * GAP, (gz - 1.5) * GAP) });
  return out;
}

interface CubieData {
  group: THREE.Group;
  gx: number;
  gy: number;
  gz: number;
  home: THREE.Vector3;
}

interface StickerMesh {
  mesh: THREE.Mesh;
  face: number;
  row: number;
  col: number;
}

interface ActiveAnim {
  turnGroup: THREE.Group;
  axis: 'x' | 'y' | 'z';
  target: number;
  startTime: number;
  duration: number;
  cubies: CubieData[];
  newState: CubeState;
  resolve: () => void;
}

export class Renderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private cubieData: CubieData[] = [];
  private stickers: StickerMesh[] = [];
  private rotateX = 0.5;
  private rotateY = -0.6;
  private isDragging = false;
  private lastMouse = { x: 0, y: 0 };
  private pivot: THREE.Group;
  private anim: ActiveAnim | null = null;

  constructor(container: HTMLElement) {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);

    this.camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    this.camera.position.set(0, 0, 10);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(this.renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffffff, 0.7);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 10, 7);
    this.scene.add(ambient, dir);

    this.pivot = new THREE.Group();
    this.scene.add(this.pivot);

    this.buildCube();
    this.setupControls(container);
    this.animate();

    window.addEventListener('resize', () => {
      this.camera.aspect = container.clientWidth / container.clientHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(container.clientWidth, container.clientHeight);
    });
  }

  private buildCube(): void {
    this.cubieData = [];
    this.stickers = [];
    while (this.pivot.children.length) this.pivot.remove(this.pivot.children[0]);

    const blackMat = new THREE.MeshLambertMaterial({ color: 0x111111 });
    const cubieGeo = new THREE.BoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE);

    cubiePositions().forEach(({ gx, gy, gz, pos }) => {
      const group = new THREE.Group();
      group.position.copy(pos);
      const body = new THREE.Mesh(cubieGeo, blackMat);
      group.add(body);
      this.pivot.add(group);
      this.cubieData.push({ group, gx, gy, gz, home: pos.clone() });
    });
  }

  private cubieAt(gx: number, gy: number, gz: number): CubieData {
    return this.cubieData.find(c => c.gx === gx && c.gy === gy && c.gz === gz)!;
  }

  updateState(state: CubeState): void {
    // Remove old stickers
    this.stickers.forEach(s => s.mesh.parent?.remove(s.mesh));
    this.stickers = [];

    const stickerGeo = new THREE.PlaneGeometry(CUBIE_SIZE * 0.85, CUBIE_SIZE * 0.85);

    const faceConfig = [
      // U face: y = +1.5, normal (0,1,0)
      { face: 0, rotation: [-Math.PI / 2, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, 1.5 * GAP + FACE_OFFSET, (r - 1.5) * GAP) },
      // D face: y = -1.5, normal (0,-1,0)
      { face: 1, rotation: [Math.PI / 2, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, -1.5 * GAP - FACE_OFFSET, (1.5 - r) * GAP) },
      // F face: z = +1.5, normal (0,0,1)
      { face: 2, rotation: [0, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, (1.5 - r) * GAP, 1.5 * GAP + FACE_OFFSET) },
      // B face: z = -1.5, normal (0,0,-1)
      { face: 3, rotation: [0, Math.PI, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((1.5 - c) * GAP, (1.5 - r) * GAP, -1.5 * GAP - FACE_OFFSET) },
      // L face: x = -1.5, normal (-1,0,0)
      { face: 4, rotation: [0, -Math.PI / 2, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3(-1.5 * GAP - FACE_OFFSET, (1.5 - r) * GAP, (1.5 - c) * GAP) },
      // R face: x = +1.5, normal (1,0,0)
      { face: 5, rotation: [0, Math.PI / 2, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3(1.5 * GAP + FACE_OFFSET, (1.5 - r) * GAP, (c - 1.5) * GAP) },
    ];

    const toGrid = (v: number) => Math.min(3, Math.max(0, Math.round(v / GAP + 1.5)));

    faceConfig.forEach(({ face, rotation, mapRC }) => {
      for (let r = 0; r < 4; r++) {
        for (let c = 0; c < 4; c++) {
          const color = state.stickers[face][r * 4 + c];
          const mat = new THREE.MeshLambertMaterial({ color: COLOR_HEX[color], side: THREE.FrontSide });
          const mesh = new THREE.Mesh(stickerGeo, mat);
          const pos = mapRC(r, c);
          // Attach the sticker to the cubie it sits on so it turns with that cubie.
          const cubie = this.cubieAt(toGrid(pos.x), toGrid(pos.y), toGrid(pos.z));
          mesh.position.copy(pos).sub(cubie.home);
          mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
          cubie.group.add(mesh);
          this.stickers.push({ mesh, face, row: r, col: c });
        }
      }
    });
  }

  // Animate a single face turn, then snap to `newState`. Resolves when done.
  // The caller is responsible for computing newState = applyMove(state, move).
  animateMove(move: MoveCode, newState: CubeState, duration: number): Promise<void> {
    return new Promise(resolve => {
      const base = move.replace(/['2]/, '');
      const suffix = move.slice(base.length);
      const face = base[0];
      const isWide = base.endsWith('w');
      const info = TURN_INFO[face];

      const layers = isWide ? info.wide : info.outer;
      const unit = info.sign * (Math.PI / 2);
      const target = suffix === "'" ? -unit : suffix === '2' ? 2 * unit : unit;

      const cubies = this.cubieData.filter(c => {
        const g = info.axis === 'x' ? c.gx : info.axis === 'y' ? c.gy : c.gz;
        return layers.includes(g);
      });

      const turnGroup = new THREE.Group();
      this.pivot.add(turnGroup);
      cubies.forEach(c => turnGroup.attach(c.group));

      this.anim = {
        turnGroup, axis: info.axis, target,
        startTime: performance.now(), duration: Math.max(1, duration),
        cubies, newState, resolve,
      };
    });
  }

  isAnimating(): boolean {
    return this.anim !== null;
  }

  private setupControls(container: HTMLElement): void {
    const onStart = (x: number, y: number) => {
      this.isDragging = true;
      this.lastMouse = { x, y };
    };
    const onMove = (x: number, y: number) => {
      if (!this.isDragging) return;
      const dx = x - this.lastMouse.x;
      const dy = y - this.lastMouse.y;
      this.rotateY += dx * 0.01;
      this.rotateX += dy * 0.01;
      this.lastMouse = { x, y };
    };
    const onEnd = () => { this.isDragging = false; };

    container.addEventListener('mousedown', e => onStart(e.clientX, e.clientY));
    window.addEventListener('mousemove', e => onMove(e.clientX, e.clientY));
    window.addEventListener('mouseup', onEnd);

    container.addEventListener('touchstart', e => {
      const t = e.touches[0];
      onStart(t.clientX, t.clientY);
    }, { passive: true });
    container.addEventListener('touchmove', e => {
      const t = e.touches[0];
      onMove(t.clientX, t.clientY);
    }, { passive: true });
    container.addEventListener('touchend', onEnd);
  }

  private stepAnim(): void {
    const a = this.anim;
    if (!a) return;
    const raw = (performance.now() - a.startTime) / a.duration;
    const t = Math.min(1, raw);
    const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // easeInOutQuad
    a.turnGroup.rotation[a.axis] = a.target * eased;

    if (t >= 1) {
      // Bake the turn: return cubies home and repaint from authoritative state.
      a.cubies.forEach(c => {
        this.pivot.add(c.group);
        c.group.position.copy(c.home);
        c.group.quaternion.identity();
      });
      this.pivot.remove(a.turnGroup);
      this.updateState(a.newState);
      this.anim = null;
      a.resolve();
    }
  }

  private animate(): void {
    requestAnimationFrame(() => this.animate());
    this.stepAnim();
    this.pivot.rotation.x = this.rotateX;
    this.pivot.rotation.y = this.rotateY;
    this.renderer.render(this.scene, this.camera);
  }

  highlightStep(stepIndex: number): void {
    // Tint stickers not involved in current step slightly darker
    void stepIndex;
  }
}
