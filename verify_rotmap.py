#!/usr/bin/env python3
"""
verify_rotmap_ursina.py
Verify rot_map values against cube.py using URSINA-CORRECT rotation matrices.

Key finding from Panda3D empirical test (set_h/set_p/set_r):
  Ursina Rx(+90) = standard Rx(+90)  = (x, -z,  y) = rotx_cw   [SAME as standard]
  Ursina Ry(+90) = (-z, y,  x)       = roty_ccw                  [NEGATED vs standard]
  Ursina Rz(+90) = ( y,-x,  z)       = rotz_ccw                  [NEGATED vs standard]

  In other words: Ursina Ry/Rz(deg) == standard Ry/Rz(-deg).
"""
import math, sys
sys.path.insert(0, 'src')
from cube import CubeState

# ── Ursina-accurate rotation functions ────────────────────────────────────────
def rot_matrix_ursina(axis, deg):
    """Return the rotation function that Ursina *actually* applies for this axis/deg."""
    r = math.radians(deg)
    c, s = round(math.cos(r), 9), round(math.sin(r), 9)
    if axis == 'x':
        # SAME as standard Rx
        return lambda x, y, z: (x, c*y - s*z, s*y + c*z)
    if axis == 'y':
        # Ursina Ry(+90) empirically = (-z,y,x), i.e. sin-terms NEGATED vs standard
        return lambda x, y, z: (c*x - s*z, y, s*x + c*z)
    if axis == 'z':
        # Ursina Rz(+90) empirically = (y,-x,z), i.e. sin-terms NEGATED vs standard
        return lambda x, y, z: (c*x + s*y, -s*x + c*y, z)

# ── Layout constants (mirrors cube.py / scratch.py) ───────────────────────────
CORNER_POSITIONS = {
    'ULB':(-0.5, 0.5, 0.5), 'URB':(0.5, 0.5, 0.5),
    'ULF':(-0.5, 0.5,-0.5), 'URF':(0.5, 0.5,-0.5),
    'DFL':(-0.5,-0.5,-0.5), 'DFR':(0.5,-0.5,-0.5),
    'DBL':(-0.5,-0.5, 0.5), 'DBR':(0.5,-0.5, 0.5),
}
POS_TO_CORNER = {v: k for k, v in CORNER_POSITIONS.items()}

# sticker index → (corner_name, face_normal_tuple)
STICKER_INFO = [
    ('ULB',(0,1,0)),('URB',(0,1,0)),('ULF',(0,1,0)),('URF',(0,1,0)),   # 0-3  U
    ('URF',(1,0,0)),('URB',(1,0,0)),('DFR',(1,0,0)),('DBR',(1,0,0)),   # 4-7  R
    ('ULF',(0,0,-1)),('URF',(0,0,-1)),('DFL',(0,0,-1)),('DFR',(0,0,-1)),# 8-11 F
    ('DFL',(0,-1,0)),('DFR',(0,-1,0)),('DBL',(0,-1,0)),('DBR',(0,-1,0)),# 12-15 D
    ('ULB',(-1,0,0)),('ULF',(-1,0,0)),('DBL',(-1,0,0)),('DFL',(-1,0,0)),# 16-19 L
    ('URB',(0,0,1)),('ULB',(0,0,1)),('DBR',(0,0,1)),('DBL',(0,0,1)),   # 20-23 B
]

def snap(v):
    return tuple(round(x * 2) / 2 for x in v)

# ── rot_map whose correctness we are testing ───────────────────────────────────
ROT_MAP = {
    'U': ('y',  1, -90),
    'D': ('y', -1,  90),
    'R': ('x',  1,  90),
    'L': ('x', -1, -90),
    'F': ('z', -1,  90),
    'B': ('z',  1, -90),
}

# ── Test each move ─────────────────────────────────────────────────────────────
def test_move(move):
    axis, face_sign, deg = ROT_MAP[move]
    R = rot_matrix_ursina(axis, deg)          # ← Ursina-accurate
    perm = CubeState.PERM_MOVES[move]
    dest  = [perm.index(i) for i in range(24)]

    face_stickers = [
        i for i, (corner, _) in enumerate(STICKER_INFO)
        if (face_sign >  0 and CORNER_POSITIONS[corner][{'x':0,'y':1,'z':2}[axis]] >  0.1)
        or (face_sign < 0 and CORNER_POSITIONS[corner][{'x':0,'y':1,'z':2}[axis]] < -0.1)
    ]

    errors = []
    for old_idx in face_stickers:
        corner_name, normal = STICKER_INFO[old_idx]
        pos    = CORNER_POSITIONS[corner_name]

        new_pos    = snap(R(*pos))
        new_normal = snap(R(*normal))
        vis_corner = POS_TO_CORNER.get(new_pos, '???')

        new_idx     = dest[old_idx]
        log_corner, log_normal = STICKER_INFO[new_idx]
        log_pos     = CORNER_POSITIONS[log_corner]

        if new_pos != snap(log_pos) or new_normal != log_normal:
            errors.append(
                f"  sticker[{old_idx:2d}] "
                f"Ursina→{vis_corner}/{new_normal}  "
                f"cube.py→{log_corner}/{log_normal}"
            )

    if errors:
        print(f"FAIL {move}  ({len(errors)} errors):")
        for e in errors: print(e)
    else:
        print(f"  OK {move}  ({len(face_stickers)} stickers)")

print("=" * 60)
print("Ursina-accurate rot_map verification")
print("=" * 60)
for m in ['U', 'D', 'R', 'L', 'F', 'B']:
    test_move(m)
print("=" * 60)
