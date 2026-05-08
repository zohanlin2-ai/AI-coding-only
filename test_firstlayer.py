"""Test full 3-sticker first-layer verification across 200 random scrambles."""
import sys, random
sys.path.insert(0, 'src')
from cube import CubeState
import solver

moves_all = ["U","U'","D","D'","R","R'","L","L'","F","F'","B","B'"]
random.seed(42)

ok = fail = bfs_fail = 0
for trial in range(200):
    cube = CubeState()
    for _ in range(8):
        cube = cube.apply(random.choice(moves_all))

    solver.compute_target_orientation(cube.state)
    t = solver.current_target_state

    path = solver.solve_first_layer(cube)
    result = cube
    for m in path:
        result = result.apply(m)

    s = result.state
    # Full 3-sticker check for all top corners
    correct = solver.face_ulf(s)
    if correct:
        ok += 1
    else:
        fail += 1
        # Diagnose which corners are wrong
        cn = {0:'W',1:'R',2:'G',3:'Y',4:'O',5:'B'}
        ulb = (s[0]==t[0] and s[16]==t[16] and s[21]==t[21])
        urb = (s[1]==t[1] and s[5]==t[5]  and s[20]==t[20])
        urf = (s[3]==t[3] and s[4]==t[4]  and s[9]==t[9])
        ulf = (s[2]==t[2] and s[17]==t[17] and s[8]==t[8])
        print(f"Trial {trial+1:3d}: FAIL  ULB={'✓' if ulb else '✗'}  "
              f"URB={'✓' if urb else '✗'}  URF={'✓' if urf else '✗'}  "
              f"ULF={'✓' if ulf else '✗'}  path_len={len(path)}")

print(f"\nResults: {ok}/200 passed, {fail}/200 failed")
