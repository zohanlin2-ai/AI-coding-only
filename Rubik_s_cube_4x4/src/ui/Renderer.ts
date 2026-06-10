import * as THREE from 'three';
import { CubeState, COLOR_HEX } from '../cube/State.js';

const CUBIE_SIZE = 0.92;
const GAP = 1.0;
const FACE_OFFSET = 0.462;

// 4x4: cubies at positions -1.5, -0.5, 0.5, 1.5 on each axis
function cubiePositions(): THREE.Vector3[] {
  const pos: THREE.Vector3[] = [];
  for (let x = 0; x < 4; x++)
    for (let y = 0; y < 4; y++)
      for (let z = 0; z < 4; z++)
        pos.push(new THREE.Vector3((x - 1.5) * GAP, (y - 1.5) * GAP, (z - 1.5) * GAP));
  return pos;
}

interface StickerMesh {
  mesh: THREE.Mesh;
  face: number;
  row: number;
  col: number;
}

export class Renderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private cubies: THREE.Group[] = [];
  private stickers: StickerMesh[] = [];
  private rotateX = 0.5;
  private rotateY = -0.6;
  private isDragging = false;
  private lastMouse = { x: 0, y: 0 };
  private pivot: THREE.Group;

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
    this.cubies = [];
    this.stickers = [];
    while (this.pivot.children.length) this.pivot.remove(this.pivot.children[0]);

    const positions = cubiePositions();
    const blackMat = new THREE.MeshLambertMaterial({ color: 0x111111 });
    const cubieGeo = new THREE.BoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE);

    positions.forEach(pos => {
      const group = new THREE.Group();
      group.position.copy(pos);
      const body = new THREE.Mesh(cubieGeo, blackMat);
      group.add(body);
      this.pivot.add(group);
      this.cubies.push(group);
    });
  }

  updateState(state: CubeState): void {
    // Remove old stickers
    this.stickers.forEach(s => s.mesh.parent?.remove(s.mesh));
    this.stickers = [];

    const stickerGeo = new THREE.PlaneGeometry(CUBIE_SIZE * 0.85, CUBIE_SIZE * 0.85);
    const positions = cubiePositions();

    // U face (face=0): y=+1.5, row from back to front (z), col left to right (x)
    // Sticker row 0 = z=-1.5, row 3 = z=+1.5 (back to front when looking from top)
    // Actually: U face row 0 = back, col 0 = left
    // Cubie index in face 0: row r, col c -> x = c-1.5, z = r-1.5 ... let's use standard orientation

    const faceConfig = [
      // U face: y = +1.5, normal (0,1,0)
      { face: 0, normal: new THREE.Vector3(0, 1, 0), rotation: [-Math.PI / 2, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, 1.5 * GAP + FACE_OFFSET, (r - 1.5) * GAP) },
      // D face: y = -1.5, normal (0,-1,0)
      { face: 1, normal: new THREE.Vector3(0, -1, 0), rotation: [Math.PI / 2, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, -1.5 * GAP - FACE_OFFSET, (1.5 - r) * GAP) },
      // F face: z = +1.5, normal (0,0,1)
      { face: 2, normal: new THREE.Vector3(0, 0, 1), rotation: [0, 0, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((c - 1.5) * GAP, (1.5 - r) * GAP, 1.5 * GAP + FACE_OFFSET) },
      // B face: z = -1.5, normal (0,0,-1)
      { face: 3, normal: new THREE.Vector3(0, 0, -1), rotation: [0, Math.PI, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3((1.5 - c) * GAP, (1.5 - r) * GAP, -1.5 * GAP - FACE_OFFSET) },
      // L face: x = -1.5, normal (-1,0,0)
      { face: 4, normal: new THREE.Vector3(-1, 0, 0), rotation: [0, -Math.PI / 2, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3(-1.5 * GAP - FACE_OFFSET, (1.5 - r) * GAP, (1.5 - c) * GAP) },
      // R face: x = +1.5, normal (1,0,0)
      { face: 5, normal: new THREE.Vector3(1, 0, 0), rotation: [0, Math.PI / 2, 0],
        mapRC: (r: number, c: number) => new THREE.Vector3(1.5 * GAP + FACE_OFFSET, (1.5 - r) * GAP, (c - 1.5) * GAP) },
    ];

    faceConfig.forEach(({ face, rotation, mapRC }) => {
      for (let r = 0; r < 4; r++) {
        for (let c = 0; c < 4; c++) {
          const color = state.stickers[face][r * 4 + c];
          const mat = new THREE.MeshLambertMaterial({ color: COLOR_HEX[color], side: THREE.FrontSide });
          const mesh = new THREE.Mesh(stickerGeo, mat);
          const pos = mapRC(r, c);
          mesh.position.copy(pos);
          mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
          this.pivot.add(mesh);
          this.stickers.push({ mesh, face, row: r, col: c });
        }
      }
    });

    // Remove unused positions variable warning
    void positions;
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

  private animate(): void {
    requestAnimationFrame(() => this.animate());
    this.pivot.rotation.x = this.rotateX;
    this.pivot.rotation.y = this.rotateY;
    this.renderer.render(this.scene, this.camera);
  }

  highlightStep(stepIndex: number): void {
    // Tint stickers not involved in current step slightly darker
    void stepIndex;
  }
}
