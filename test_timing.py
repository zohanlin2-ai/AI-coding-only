"""Time the second layer (OLL+PLL) specifically, separately from first layer."""
import sys, random, time
sys.path.insert(0, 'src')
from cube import CubeState
import solver

moves_all = ["U","U'","D","D'","R","R'","L","L'","F","F'","B","B'"]
random.seed(42)

# Pre-solve first layer for all 200 states
states_after_fl = []
for trial in range(200):
    cube = CubeState()
    for _ in range(8):
        cube = cube.apply(random.choice(moves_all))
    solver.compute_target_orientation(cube.state)
    path = solver.solve_first_layer(cube)
    cube = solver.apply_seq(cube, path)
    states_after_fl.append((cube, solver.current_target_state))

print("First layer pre-computed. Now timing OLL+PLL...")

oll_times = []
pll_times = []
ok = fail_oll = fail_pll = 0

for i, (cube, ts) in enumerate(states_after_fl):
    solver.current_target_state = ts

    t0 = time.perf_counter()
    path_oll = solver.solve_bottom_oll(cube)
    t1 = time.perf_counter()
    cube2 = solver.apply_seq(cube, path_oll)

    t2 = time.perf_counter()
    path_pll = solver.solve_bottom_pll(cube2)
    t3 = time.perf_counter()
    cube3 = solver.apply_seq(cube2, path_pll)

    oll_times.append(t1 - t0)
    pll_times.append(t3 - t2)

    if cube3.is_solved():
        ok += 1
    else:
        fail_pll += 1
        print(f"Trial {i+1}: FAIL (PLL)")

print(f"\nFull solve: {ok}/200")
print(f"OLL avg: {sum(oll_times)/len(oll_times)*1000:.1f}ms  max: {max(oll_times)*1000:.1f}ms")
print(f"PLL avg: {sum(pll_times)/len(pll_times)*1000:.1f}ms  max: {max(pll_times)*1000:.1f}ms")

slow_oll = sorted([(t,i) for i,t in enumerate(oll_times)], reverse=True)[:5]
slow_pll = sorted([(t,i) for i,t in enumerate(pll_times)], reverse=True)[:5]
print(f"Slowest OLL: {[(f'{t*1000:.0f}ms', 'trial', i+1) for t,i in slow_oll]}")
print(f"Slowest PLL: {[(f'{t*1000:.0f}ms', 'trial', i+1) for t,i in slow_pll]}")
