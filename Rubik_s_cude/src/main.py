# src/main.py
from ursina import *
import random
from cube import CubeState
app = Ursina()

# --- Visual Cube Setup ---
pieces = []
colors_map = {
    'U': color.white,
    'D': color.yellow,
    'L': color.orange,
    'R': color.red,
    'F': color.green,
    'B': color.blue
}

# Create 8 pieces
for x in [-0.5, 0.5]:
    for y in [-0.5, 0.5]:
        for z in [-0.5, 0.5]:
            p = Entity(model='cube', scale=0.95, position=(x, y, z), color=color.gray)
            
            # Add colored faces (Using 0.51 to prevent z-fighting with the grey cube and double_sided to ensure visibility)
            eps = 0.51
            if y == 0.5: Entity(parent=p, model='quad', position=(0,eps,0), rotation=(-90,0,0), color=colors_map['U'], double_sided=True)
            if y == -0.5: Entity(parent=p, model='quad', position=(0,-eps,0), rotation=(90,0,0), color=colors_map['D'], double_sided=True)
            if x == 0.5: Entity(parent=p, model='quad', position=(eps,0,0), rotation=(0,90,0), color=colors_map['R'], double_sided=True)
            if x == -0.5: Entity(parent=p, model='quad', position=(-eps,0,0), rotation=(0,-90,0), color=colors_map['L'], double_sided=True)
            if z == -0.5: Entity(parent=p, model='quad', position=(0,0,-eps), rotation=(0,0,0), color=colors_map['F'], double_sided=True)
            if z == 0.5: Entity(parent=p, model='quad', position=(0,0,eps), rotation=(0,180,0), color=colors_map['B'], double_sided=True)
            
            pieces.append(p)

pivot = Entity()

# GUI logic matching cube.py definition
# Rotation degrees for Clockwise looking AT the face
# Ursina uses left-handed coords? No, it's (x:Right, y:Up, z:Forward)
rot_map = {
    # Derived from Ursina source: rotation_directions=(-1,-1,1)
    # => rotation_y=V  maps to Panda3D H=-V
    # => rotation_x=V  maps to Panda3D P=-V
    # => rotation_z=V  maps to Panda3D R=+V
    #
    # Panda3D empirical (set_h/set_p/set_r on child at (1,0,0)):
    #   H=-90 → child→(0,0,-1)_ursina → x→-z → roty_cw   → U (+90 gives H=-90)
    #   H=+90 → child→(0,0,+1)_ursina → x→+z → roty_ccw  → D (-90 gives H=+90)
    #   P=-90 → camera above           →       rotx_cw    → R (+90 gives P=-90)
    #   R=+90 → child→(0,-1,0)_ursina → x→-y → rotz_ccw  → F (+90 gives R=+90)
    'U': ('y',  1,  90),  # Ry(90)→H=-90 → roty_cw  = (z, y,-x) ✓
    'D': ('y', -1, -90),  # Ry(-90)→H=+90 → roty_ccw = (-z,y, x) ✓
    'R': ('x',  1,  90),  # Rx(90)→P=-90 → rotx_cw  = (x,-z, y) ✓
    'L': ('x', -1, -90),  # Rx(-90)→P=-90neg → rotx_ccw= (x, z,-y) ✓
    'F': ('z', -1,  90),  # Rz(90)→R=+90 → rotz_ccw = (y,-x, z) ✓
    'B': ('z',  1, -90),  # Rz(-90)→R=-90 → rotz_cw  = (-y,x, z) ✓
}

inverse_moves = {
    "U'": "U", "R'": "R", "F'": "F", "D'": "D", "L'": "L", "B'": "B",
    "U": "U'", "R": "R'", "F": "F'", "D": "D'", "L": "L'", "B": "B'"
}

from solver import solve_phase

action_queue = []
is_animating = False
is_solving = False
solve_phase_index = 0
target_phase_index = 0

logic_cube = CubeState()

# GUI Status Text
status_text = Text(text='Status: Idle', origin=(-0.5, 0.5), position=(-0.85, 0.48), color=color.yellow, scale=1.5)
color_info_text = Text(text='Best face: -', origin=(-0.5, 0.5), position=(-0.85, 0.43), color=color.lime, scale=1.2)

COLOR_NAMES   = {0: 'White', 1: 'Red', 2: 'Green', 3: 'Yellow', 4: 'Orange', 5: 'Blue'}

def update_color_info():
    """Scan every face, find which color has the most stickers on a single face,
       and display it so the user can verify colour detection before solving."""
    import solver
    best_color, best_count, best_face = 0, 0, '?'
    face_letters = ['U', 'R', 'F', 'D', 'L', 'B']
    for fi, start in enumerate([0, 4, 8, 12, 16, 20]):
        face = logic_cube.state[start:start+4]
        for c_id in range(6):
            cnt = face.count(c_id)
            if cnt > best_count:
                best_count = cnt
                best_color = c_id
                best_face = face_letters[fi]
    target_color_id = solver.current_target_state[0]
    target_name = COLOR_NAMES.get(target_color_id, str(target_color_id))
    best_name = COLOR_NAMES.get(best_color, str(best_color))
    color_info_text.text = f'Best: {best_name} x{best_count} ({best_face} face)  |  Solver target: {target_name}'

def perform_move_animation(move_str, speed=0.3):
    global is_animating
    is_animating = True
    base_move = move_str[0]
    is_inverse = "'" in move_str
    
    axis_name, sign, deg = rot_map[base_move]
    if is_inverse:
        deg = -deg
    
    # Select pieces
    face_pieces = []
    for p in pieces:
        val = getattr(p.world_position, axis_name)
        if (sign > 0 and val > 0.1) or (sign < 0 and val < -0.1):
            face_pieces.append(p)
            
    pivot.rotation = (0,0,0)
    for p in face_pieces:
        p.world_parent = pivot
        
    kwargs = {"duration": speed, "curve": curve.in_out_sine}
    pivot.animate(f"rotation_{axis_name}", deg, **kwargs)
    
    def end_anim():
        global is_animating
        for p in face_pieces:
            p.world_parent = scene
        pivot.rotation = (0,0,0)
        is_animating = False
        check_queue()
        
    invoke(end_anim, delay=speed + 0.05)

def check_queue():
    global is_solving, solve_phase_index
    if not is_animating:
        if len(action_queue) > 0:
            move = action_queue.pop(0)
            if not is_solving:
                status_text.text = f'Status: Animating ({move})'
            perform_move_animation(move, speed=0.15 if (len(action_queue) > 0 or is_solving) else 0.3)

        elif is_solving:
            import solver
            target_name = COLOR_NAMES.get(
                solver.current_target_state[0] if hasattr(solver, 'current_target_state') else 0, '?'
            )
            phase_names = [
                f"Top Layer [{target_name} up]",
                f"Bottom OLL [{target_name} up]",
                f"Bottom PLL [{target_name} up]"
            ]
            while solve_phase_index < target_phase_index:
                status_text.text = f'Status: Computing {phase_names[solve_phase_index]}...'
                path = solve_phase(logic_cube, solve_phase_index)
                solve_phase_index += 1
                if path:
                    for m in path: do_move(m)
                    status_text.text = f'Status: Animating {phase_names[solve_phase_index - 1]}'
                    return

            if target_phase_index < 3:
                is_solving = False
                update_color_info()
                import solver as _s
                t = _s.current_target_state
                s = logic_cube.state
                # Full first-layer check: all 3 stickers of each top corner
                verified = _s.face_ulf(s)
                cn = {0:'W',1:'R',2:'G',3:'Y',4:'O',5:'B'}
                print(f"[Verify] target={COLOR_NAMES.get(t[0],'?')}  "
                      f"ULB({cn.get(s[0],'?')},{cn.get(s[16],'?')},{cn.get(s[21],'?')})"
                      f" URB({cn.get(s[1],'?')},{cn.get(s[5],'?')},{cn.get(s[20],'?')})"
                      f" ULF({cn.get(s[2],'?')},{cn.get(s[17],'?')},{cn.get(s[8],'?')})"
                      f" URF({cn.get(s[3],'?')},{cn.get(s[4],'?')},{cn.get(s[9],'?')})"
                      f"  {'OK ✓' if verified else 'FAIL'}")
                if verified:
                    status_text.text = f'Status: First Layer Done [{target_name} verified ✓]'
                else:
                    status_text.text = f'Status: First Layer FAILED [{target_name}]'
            else:
                if not logic_cube.is_solved():
                    # Retry just OLL+PLL — first layer is already correct
                    status_text.text = 'Status: Fallback retry (OLL)...'
                    solve_phase_index = 1
                    do_move(random.choice(["D", "D'"]))
                    return
                else:
                    is_solving = False
                    update_color_info()
                    status_text.text = 'Status: Fully Solved! ✓'
        else:
            update_color_info()
            if logic_cube.is_solved():
                status_text.text = 'Status: Solved! ✓'
            else:
                status_text.text = 'Status: Idle'

def do_move(m):
    global logic_cube
    logic_cube = logic_cube.apply(m)
    action_queue.append(m)
    check_queue()

def on_random_click():
    global solve_phase_index
    if is_animating or len(action_queue) > 0 or is_solving: return
    status_text.text = 'Status: Scrambling...'
    solve_phase_index = 0
    possible = ["U", "U'", "R", "R'", "F", "F'", "D", "D'", "L", "L'", "B", "B'"]
    for _ in range(8): do_move(random.choice(possible))

def on_first_layer_click():
    global is_solving, solve_phase_index, target_phase_index
    if is_animating or len(action_queue) > 0 or is_solving: return
    if logic_cube.is_solved(): return

    import solver
    best_c = solver.compute_target_orientation(logic_cube.state)
    top_color = COLOR_NAMES.get(best_c, str(best_c))
    update_color_info()

    status_text.text = f'Status: Starting First Layer  [{top_color} to top]'
    is_solving = True
    solve_phase_index = 0
    target_phase_index = 1
    check_queue()

def on_second_layer_click():
    global is_solving, solve_phase_index, target_phase_index
    if is_animating or len(action_queue) > 0 or is_solving: return
    if logic_cube.is_solved(): return

    import solver
    top_color = COLOR_NAMES.get(solver.current_target_state[0], '?')
    status_text.text = f'Status: Starting Second Layer  [{top_color} up]'
    is_solving = True
    solve_phase_index = 1   # Skip phase 0 (first layer already done)
    target_phase_index = 3
    check_queue()

# UI Buttons for functionality
Button(text='Random', color=color.azure, position=(-0.4, -0.4), scale=(0.15, 0.05), on_click=on_random_click)
Button(text='First Layer', color=color.cyan, position=(0, -0.4), scale=(0.15, 0.05), on_click=on_first_layer_click)
Button(text='Second Layer', color=color.green, position=(0.4, -0.4), scale=(0.16, 0.05), on_click=on_second_layer_click)



# Camera Setup to make it look 3D instead of flat
camera_pivot = Entity()
camera.parent = camera_pivot
camera.position = (0, 0, -7)
camera_pivot.rotation = (30, -45, 0) # Initial isometric view

def cam_left(): camera_pivot.animate("rotation_y", camera_pivot.rotation_y - 90, duration=0.3)
def cam_right(): camera_pivot.animate("rotation_y", camera_pivot.rotation_y + 90, duration=0.3)
def cam_up(): camera_pivot.animate("rotation_x", camera_pivot.rotation_x - 90, duration=0.3)
def cam_down(): camera_pivot.animate("rotation_x", camera_pivot.rotation_x + 90, duration=0.3)

# 4 Buttons to inspect the faces
Button(text='←', position=(-0.8, 0), scale=(0.05, 0.1), on_click=cam_left)
Button(text='→', position=(0.8, 0), scale=(0.05, 0.1), on_click=cam_right)
Button(text='↑', position=(0, 0.45), scale=(0.1, 0.05), on_click=cam_up)
Button(text='↓', position=(0, -0.45), scale=(0.1, 0.05), on_click=cam_down)

# We still enable EditorCamera so you can use right-click to drag freely if wanted
ed_cam = EditorCamera()
ed_cam.enabled = False # disable the default free control to prevent conflict with buttons

app.run()
