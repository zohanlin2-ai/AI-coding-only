import json

stickers = []

# U face (y=1) -> 0..3: ULB (-1,1,1), URB (1,1,1), ULF (-1,1,-1), URF (1,1,-1)
stickers += [((-1,1,1), (0,1,0)), ((1,1,1), (0,1,0)), ((-1,1,-1), (0,1,0)), ((1,1,-1), (0,1,0))]
# R face (x=1) -> 4..7: URF (1,1,-1), URB (1,1,1), DFR (1,-1,-1), DBR (1,-1,1)
stickers += [((1,1,-1), (1,0,0)), ((1,1,1), (1,0,0)), ((1,-1,-1), (1,0,0)), ((1,-1,1), (1,0,0))]
# F face (z=-1)-> 8..11: ULF (-1,1,-1), URF (1,1,-1), DFL (-1,-1,-1), DFR (1,-1,-1)
stickers += [((-1,1,-1), (0,0,-1)), ((1,1,-1), (0,0,-1)), ((-1,-1,-1), (0,0,-1)), ((1,-1,-1), (0,0,-1))]
# D face (y=-1)-> 12..15: DFL (-1,-1,-1), DFR (1,-1,-1), DBL (-1,-1,1), DBR (1,-1,1)
stickers += [((-1,-1,-1), (0,-1,0)), ((1,-1,-1), (0,-1,0)), ((-1,-1,1), (0,-1,0)), ((1,-1,1), (0,-1,0))]
# L face (x=-1)-> 16..19: ULB (-1,1,1), ULF (-1,1,-1), DBL (-1,-1,1), DFL (-1,-1,-1)
stickers += [((-1,1,1), (-1,0,0)), ((-1,1,-1), (-1,0,0)), ((-1,-1,1), (-1,0,0)), ((-1,-1,-1), (-1,0,0))]
# B face (z=1) -> 20..23: URB (1,1,1), ULB (-1,1,1), DBR (1,-1,1), DBL (-1,-1,1)
stickers += [((1,1,1), (0,0,1)), ((-1,1,1), (0,0,1)), ((1,-1,1), (0,0,1)), ((-1,-1,1), (0,0,1))]

def rotx_cw(pt, n): 
    return (pt[0], -pt[2], pt[1]), (n[0], -n[2], n[1])
def roty_cw(pt, n): 
    return (pt[2], pt[1], -pt[0]), (n[2], n[1], -n[0])
def rotz_cw(pt, n): 
    return (-pt[1], pt[0], pt[2]), (-n[1], n[0], n[2])

def rotx_ccw(pt, n): 
    return (pt[0], pt[2], -pt[1]), (n[0], n[2], -n[1])
def roty_ccw(pt, n): 
    return (-pt[2], pt[1], pt[0]), (-n[2], n[1], n[0])
def rotz_ccw(pt, n): 
    return (pt[1], -pt[0], pt[2]), (n[1], -n[0], n[2])

moves = {
    'R': rotx_cw, 'L': rotx_ccw,
    'U': roty_cw, 'D': roty_ccw,
    'B': rotz_cw, 'F': rotz_ccw
}

for m_name, rot_func in moves.items():
    perm = []
    for i in range(24):
        pt, n = stickers[i]
        
        if (m_name=='R' and pt[0]==1) or (m_name=='L' and pt[0]==-1) or \
           (m_name=='U' and pt[1]==1) or (m_name=='D' and pt[1]==-1) or \
           (m_name=='F' and pt[2]==-1) or (m_name=='B' and pt[2]==1):
            
            # Find the piece that MOVES TO (pt, n) under rot_func!
            # Since rot_func is applied to the starting state, the color ending up at (pt, n)
            # is the one that started at rot_func_inverse(pt, n).
            pass
            
    # actually, `new_state[i] = old_state[perm[i]]`
    # meaning the sticker ending up at index `i` is the one that started at `perm[i]`.
    for i in range(24):
        pt, n = stickers[i]
        
        if (m_name=='R' and pt[0]==1) or (m_name=='L' and pt[0]==-1) or \
           (m_name=='U' and pt[1]==1) or (m_name=='D' and pt[1]==-1) or \
           (m_name=='F' and pt[2]==-1) or (m_name=='B' and pt[2]==1):
           
            # Find source pt by rotating (pt, n) with the inverse function!
            # Or simply, apply rot_func to all points, and find which one maps to (pt, n)
            source_idx = -1
            for j in range(24):
                rp, rn = rot_func(stickers[j][0], stickers[j][1])
                if rp == pt and rn == n:
                    source_idx = j
                    break
            perm.append(source_idx)
        else:
            perm.append(i)
            
    print(f"'{m_name}': {perm},")
