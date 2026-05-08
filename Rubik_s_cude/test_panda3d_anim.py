"""
Definitive animation test using raw Panda3D (no display needed).
Mimics exactly what perform_move_animation does:
  1. Parent piece to pivot
  2. Set pivot rotation via Ursina's setHpr formula
  3. Unparent piece back to root
  4. Check final world position

Expected: each move's rot_map angle should move pieces exactly
as cube.py's PERM_MOVES says.
"""
import sys
sys.path.insert(0, 'src')

from panda3d.core import NodePath
from cube import CubeState

# ─── Ursina rotation mapping (from Ursina entity.py) ──────────────────────
# rotation_directions = (-1, -1, 1)
# setHpr(Vec3(rot_y, rot_x, rot_z) * (-1, -1, 1))
# => H = -rot_y,  P = -rot_x,  R = rot_z

def apply_ursina_rotation(pivot, rx, ry, rz):
    """Apply Ursina entity.rotation = (rx, ry, rz) to a pivot NodePath."""
    pivot.setHpr(-ry, -rx, rz)  # matches Ursina's rotation_setter

# ─── rot_map we want to test ───────────────────────────────────────────────
ROT_MAP = {
    'U': ('y',  1,  90),
    'D': ('y', -1, -90),
    'R': ('x',  1,  90),
    'L': ('x', -1, -90),
    'F': ('z', -1,  90),
    'B': ('z',  1, -90),
}

CORNER_POSITIONS = {
    'ULB': (-0.5, 0.5, 0.5), 'URB': (0.5, 0.5, 0.5),
    'ULF': (-0.5, 0.5,-0.5), 'URF': (0.5, 0.5,-0.5),
    'DFL': (-0.5,-0.5,-0.5), 'DFR': (0.5,-0.5,-0.5),
    'DBL': (-0.5,-0.5, 0.5), 'DBR': (0.5,-0.5, 0.5),
}

STICKER_INFO = [
    ('ULB',(0,1,0)),('URB',(0,1,0)),('ULF',(0,1,0)),('URF',(0,1,0)),
    ('URF',(1,0,0)),('URB',(1,0,0)),('DFR',(1,0,0)),('DBR',(1,0,0)),
    ('ULF',(0,0,-1)),('URF',(0,0,-1)),('DFL',(0,0,-1)),('DFR',(0,0,-1)),
    ('DFL',(0,-1,0)),('DFR',(0,-1,0)),('DBL',(0,-1,0)),('DBR',(0,-1,0)),
    ('ULB',(-1,0,0)),('ULF',(-1,0,0)),('DBL',(-1,0,0)),('DFL',(-1,0,0)),
    ('URB',(0,0,1)),('ULB',(0,0,1)),('DBR',(0,0,1)),('DBL',(0,0,1)),
]

def snap(v):
    return tuple(round(x * 2) / 2 for x in v)

def panda_to_ursina(ppos):
    """Convert Panda3D (x,y,z) world position to Ursina (x,y,z)."""
    # Panda3D: x=right, y=forward(into scene), z=up
    # Ursina:  x=right, z=forward(into scene), y=up
    x_p, y_p, z_p = ppos
    return (x_p, z_p, y_p)

def test_move(move_name):
    axis, face_sign, deg = ROT_MAP[move_name]
    perm = CubeState.PERM_MOVES[move_name]
    dest = [perm.index(i) for i in range(24)]  # dest[i] = where sticker i ends up

    # Build scene hierarchy
    root  = NodePath("root")
    pivot = NodePath("pivot")
    pivot.reparentTo(root)

    errors = []

    # Test each sticker on this face
    for old_idx in range(24):
        corner_name, normal_ursina = STICKER_INFO[old_idx]
        pos_ursina = CORNER_POSITIONS[corner_name]

        # Is this sticker on the face being rotated?
        axis_i = {'x': 0, 'y': 1, 'z': 2}[axis]
        on_face = (face_sign > 0 and pos_ursina[axis_i] > 0.1) or \
                  (face_sign < 0 and pos_ursina[axis_i] < -0.1)
        if not on_face:
            continue

        # --- Simulate perform_move_animation ---
        # Create piece at Ursina position → convert to Panda3D for NodePath
        # Panda3D pos = (x_u, z_u, y_u)  [swap y↔z]
        piece = NodePath("piece")
        piece.reparentTo(root)
        x_u, y_u, z_u = pos_ursina
        piece.setPos(x_u, z_u, y_u)  # set in Panda3D coords

        # Parent to pivot (pivot at origin, no rotation)
        pivot.setHpr(0, 0, 0)
        piece.wrtReparentTo(pivot)  # wrtReparentTo preserves world transform

        # Apply Ursina rotation to pivot
        rx = deg if axis == 'x' else 0
        ry = deg if axis == 'y' else 0
        rz = deg if axis == 'z' else 0
        apply_ursina_rotation(pivot, rx, ry, rz)

        # Unparent back to root (preserving world transform)
        piece.wrtReparentTo(root)

        # Read final world position and convert to Ursina
        ppos = piece.getPos(root)
        new_pos_ursina = panda_to_ursina((ppos.x, ppos.y, ppos.z))
        new_pos_ursina = snap(new_pos_ursina)

        # What does cube.py say the destination should be?
        new_idx = dest[old_idx]
        new_corner, new_normal = STICKER_INFO[new_idx]
        expected_pos = snap(CORNER_POSITIONS[new_corner])

        piece.removeNode()

        if new_pos_ursina != expected_pos:
            errors.append(
                f"  sticker[{old_idx:2d}] {corner_name} → "
                f"visual:{new_pos_ursina}  logic:{expected_pos} ({new_corner})"
            )

    pivot.removeNode()
    root.removeNode()

    if errors:
        print(f"FAIL {move_name}  ({len(errors)} position errors):")
        for e in errors: print(e)
    else:
        print(f"  OK {move_name}")

print("=" * 60)
print("Panda3D world-position animation test (matches perform_move_animation)")
print(f"Testing rot_map: U=+90, D=-90, R=+90, L=-90, F=+90, B=-90")
print("=" * 60)
for m in ['U', 'D', 'R', 'L', 'F', 'B']:
    test_move(m)
print("=" * 60)
