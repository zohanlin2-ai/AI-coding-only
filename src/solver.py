from collections import deque
from cube import CubeState

basic_moves = [["U"], ["U'"], ["D"], ["D'"], ["R"], ["R'"], ["L"], ["L'"], ["F"], ["F'"], ["B"], ["B'"]]

# Mathematical Macro Filtering to prevent destructive looping (Fixes Freezes)
all_manipulators = [
    ["R'", "D'", "R"], ["R'", "D'", "R", "D"], ["R'", "D", "R"], # Right Face (URF)
    ["F", "D", "F'"], ["F", "D", "F'", "D'"], ["F", "D'", "F'"], # Front Face (URF)
    
    ["L", "D", "L'"], ["L", "D", "L'", "D'"], ["L", "D'", "L'"], # Left Face (ULF)
    ["F'", "D'", "F"], ["F'", "D'", "F", "D"], ["F'", "D", "F"], # Front Face (ULF)

    ["L'", "D'", "L"], ["L'", "D'", "L", "D"], ["L'", "D", "L"], # Left Face (ULB)
    ["B", "D", "B'"], ["B", "D", "B'", "D'"], ["B", "D'", "B'"], # Back Face (ULB)

    ["R", "D", "R'"], ["R", "D", "R'", "D'"], ["R", "D'", "R'"], # Right Face (URB)
    ["B'", "D'", "B"], ["B'", "D'", "B", "D"], ["B'", "D", "B"], # Back Face (URB)
]

standalone = [["D"], ["D'"], ["D", "D"]]

macros_1 = standalone + all_manipulators
macros_2 = standalone + [m for m in all_manipulators if m[0] not in ["L'", "B"]]
macros_3 = standalone + [m for m in all_manipulators if m[0] not in ["L'", "B", "B'", "R"]]
macros_4 = standalone + [m for m in all_manipulators if m[0] not in ["L'", "B", "B'", "R", "R'", "F"]]

# Global variable to hold the dynamic target state for Color Neutral logic
current_target_state = tuple(i // 4 for i in range(24)) # Default to White Top

_solved_24_cache = None  # Generated once, reused for the entire session

def get_24_solved_states():
    global _solved_24_cache
    if _solved_24_cache is not None:
        return _solved_24_cache
    from collections import deque
    base = tuple(i // 4 for i in range(24))
    states = set([base])
    queue = deque([base])
    
    def apply_batch(s, moves):
        c = CubeState(s)
        for m in moves: c = c.apply(m)
        return c.state
        
    # Global whole-cube rotations
    # X (Pitch) = R L', Y (Yaw) = U D', Z (Roll) = F B'
    rotations = [ ["R", "L'"], ["U", "D'"], ["F", "B'"], ["R'", "L"], ["U'", "D"], ["F'", "B"] ]
    while queue:
        curr = queue.popleft()
        for rot in rotations:
            nxt = apply_batch(curr, rot)
            if nxt not in states:
                states.add(nxt)
                queue.append(nxt)
    _solved_24_cache = list(states)
    return _solved_24_cache

def compute_target_orientation(current_state):
    global current_target_state
    max_cnt = -1
    best_color = 0
    # Scan all 6 faces to find the most assembled color
    for start in [0, 4, 8, 12, 16, 20]:
        face = current_state[start:start+4]
        for c in range(6):
            cnt = face.count(c)
            if cnt > max_cnt:
                max_cnt = cnt
                best_color = c
                if max_cnt == 4: break

    # Among all solved states with best_color on U, pick the one that
    # shares the MOST stickers with the current state — this minimises
    # BFS work because fewer corners need to move.
    solved24 = get_24_solved_states()
    candidates = [s for s in solved24
                  if s[0] == best_color and s[1] == best_color
                  and s[2] == best_color and s[3] == best_color]

    best_match, best_ts = -1, candidates[0]
    for ts in candidates:
        match = sum(1 for i in range(24) if current_state[i] == ts[i])
        if match > best_match:
            best_match, best_ts = match, ts

    current_target_state = best_ts
    return best_color


# Full corner verifiers — check all 3 stickers per top corner:
#   U sticker AND both side stickers must match the chosen target orientation.
# Sticker indices (from STICKER_INFO):
#   ULB: s[0]=U  s[16]=L  s[21]=B
#   URB: s[1]=U  s[5]=R   s[20]=B
#   ULF: s[2]=U  s[17]=L  s[8]=F
#   URF: s[3]=U  s[4]=R   s[9]=F
def face_ulb(s):
    t = current_target_state
    return s[0]==t[0] and s[16]==t[16] and s[21]==t[21]

def face_urb(s):
    t = current_target_state
    return face_ulb(s) and s[1]==t[1] and s[5]==t[5] and s[20]==t[20]

def face_urf(s):
    t = current_target_state
    return face_urb(s) and s[3]==t[3] and s[4]==t[4] and s[9]==t[9]

def face_ulf(s):
    """True when all 4 top-layer corners are correctly placed AND oriented."""
    t = current_target_state
    return face_urf(s) and s[2]==t[2] and s[17]==t[17] and s[8]==t[8]


def apply_seq(cube, seq):
    for m in seq:
        cube = cube.apply(m)
    return cube

MAX_BFS_STATES = 150_000  # Raised to handle full 3-sticker corner search

def bfs_phase(cube_state, goal_func, allowed_macros):
    if goal_func(cube_state.state): return []
    start_state = cube_state.state
    visited = {start_state: None}
    queue = deque([start_state])

    while queue:
        if len(visited) > MAX_BFS_STATES:
            print(f"[BFS] Safety cap reached ({MAX_BFS_STATES} states). Aborting.")
            return []  # Give up safely instead of hanging forever
        curr_tuple = queue.popleft()
        for macro in allowed_macros:
            nxt_cube = CubeState(curr_tuple)
            nxt_cube = apply_seq(nxt_cube, macro)
            nxt = nxt_cube.state
            if nxt not in visited:
                visited[nxt] = (curr_tuple, macro)
                if goal_func(nxt):
                    path, c = [], nxt
                    while visited[c] is not None:
                        prev, mac = visited[c]
                        path.insert(0, mac)
                        c = prev
                    return [m for mac in path for m in mac]
                queue.append(nxt)
    return []

# === Phase 1: First Layer — place all 4 target-color stickers on U face ===
def solve_first_layer(cube):
    """Place target-colour stickers on U face one corner at a time.
    Each step only checks the U-face sticker (not the side stickers)."""
    full_path = []

    steps = [
        (face_ulb, macros_1, "ULB"),
        (face_urb, macros_2, "URB"),
        (face_urf, macros_3, "URF"),
        (face_ulf, macros_4, "ULF"),
    ]

    for goal, macros, name in steps:
        for attempt in range(4):          # up to 4 D-rotation retries
            if goal(cube.state):
                break
            p = bfs_phase(cube, goal, macros)
            if p:
                full_path.extend(p)
                cube = apply_seq(cube, p)
                break
            # BFS found nothing — rotate D layer to unlock and retry
            cube = cube.apply("D")
            full_path.append("D")

    return full_path

# Mathematical Transform for Second Layer (Flipping U algorithms to affect D face precisely)
def map_d(alg):
    m_map = { "U": "D", "U'": "D'", "R": "L", "R'": "L'", "F": "F", "F'": "F'", "L": "R", "L'": "R'", "B": "B", "B'": "B'", "D": "U", "D'": "U'" }
    return [m_map[m] for m in alg]

# === Phase 2: Second Layer OLL (Orient yellow/opposite face without messing up Top) ===
def solve_bottom_oll(cube):
    if cube.state[12] == current_target_state[12] and cube.state[13] == current_target_state[13] and cube.state[14] == current_target_state[14] and cube.state[15] == current_target_state[15]:
        return []
    
    oll_macros = [
        ["D"], ["D'"],
        map_d(["R", "U", "R'", "U", "R", "U", "U", "R'"]),                             # Sune -> Bottom Sune
        map_d(["R", "U", "U", "R'", "U'", "R", "U'", "R'"]),                            # Anti-Sune
        map_d(["R", "R", "U", "U", "R", "U", "U", "R", "R"]),                           # H
        map_d(["R", "U", "U", "R", "R", "U'", "R", "R", "U'", "R", "R", "U", "U", "R"]),# Pi
        map_d(["F", "R", "U", "R'", "U'", "F'"]),                                       # Headlights
        map_d(["R", "U", "R'", "U'", "R'", "F", "R", "F'"]),                            # T
        map_d(["F", "R", "U", "R'", "U'", "R", "U", "R'", "U'", "F'"])                  # U
    ]
    return bfs_phase(cube, lambda s: s[12] == current_target_state[12] and s[13] == current_target_state[13] and s[14] == current_target_state[14] and s[15] == current_target_state[15], oll_macros)

# === Phase 3: Second Layer PLL (Permute last edges to perfect state) ===
def solve_bottom_pll(cube):
    pll_macros = [
        ["D"], ["D'"], ["D", "D"],
        map_d(["R", "U", "R'", "U'", "R'", "F", "R", "R", "U'", "R'", "U'", "R", "U", "R'", "F'"]), # T-Perm
        map_d(["F", "R", "U'", "R'", "U'", "R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R", "F'"]) # Y-Perm
    ]
    return bfs_phase(cube, lambda c: tuple(c) == current_target_state, pll_macros)

# Entry Point
def solve_phase(cube_state, phase_index):
    try:
        if phase_index == 0: return solve_first_layer(cube_state)
        elif phase_index == 1: return solve_bottom_oll(cube_state)
        elif phase_index == 2: return solve_bottom_pll(cube_state)
    except Exception as e:
        print("Solver Phase Error:", e)
    return []
