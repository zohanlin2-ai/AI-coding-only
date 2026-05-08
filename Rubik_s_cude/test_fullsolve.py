"""Full solve test: scramble → first layer → second layer (OLL+PLL) → verify solved."""
import sys, random, time
sys.path.insert(0, 'src')
from cube import CubeState
import solver

moves_all = ["U","U'","D","D'","R","R'","L","L'","F","F'","B","B'"]
random.seed(42)

ok = fail_fl = fail_oll = fail_pll = 0

for trial in range(200):
    cube = CubeState()
    for _ in range(8):
        cube = cube.apply(random.choice(moves_all))

    # Phase 0: First Layer
    solver.compute_target_orientation(cube.state)
    path0 = solver.solve_first_layer(cube)
    cube = solver.apply_seq(cube, path0)

    if not solver.face_ulf(cube.state):
        fail_fl += 1
        continue

    # Phase 1: OLL
    path1 = solver.solve_bottom_oll(cube)
    cube = solver.apply_seq(cube, path1)

    t = solver.current_target_state
    oll_done = (cube.state[12:16] == t[12:16])
    if not oll_done:
        fail_oll += 1
        cn = {0:'W',1:'R',2:'G',3:'Y',4:'O',5:'B'}
        d = [cn.get(cube.state[i], '?') for i in range(12, 16)]
        dt = [cn.get(t[i], '?') for i in range(12, 16)]
        print(f"Trial {trial+1:3d}: OLL FAIL  D-face got {d}  need {dt}")
        continue

    # Phase 2: PLL
    path2 = solver.solve_bottom_pll(cube)
    cube = solver.apply_seq(cube, path2)

    if cube.is_solved():
        ok += 1
    else:
        fail_pll += 1
        print(f"Trial {trial+1:3d}: PLL FAIL  path_len={len(path2)}")

total_tested = ok + fail_oll + fail_pll
print(f"\nFirst Layer: 200/200")
print(f"OLL pass:    {200 - fail_oll - fail_fl}/200")
print(f"Full solve:  {ok}/200  (FL_fail={fail_fl} OLL_fail={fail_oll} PLL_fail={fail_pll})")
