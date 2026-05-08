# src/cube.py

class CubeState:
    # 24 sticker state representing a 2x2x2 cube
    # 0..3: U, 4..7: R, 8..11: F, 12..15: D, 16..19: L, 20..23: B
    # Solved is implicitly group of 4s: (0,0,0,0, 1,1,1,1, ...)

    PERM_MOVES = {
        'U': [2, 0, 3, 1, 20, 21, 6, 7, 4, 5, 10, 11, 12, 13, 14, 15, 8, 9, 18, 19, 16, 17, 22, 23],
        'D': [0, 1, 2, 3, 4, 5, 10, 11, 8, 9, 18, 19, 14, 12, 15, 13, 16, 17, 22, 23, 20, 21, 6, 7],
        'F': [0, 1, 19, 17, 2, 5, 3, 7, 10, 8, 11, 9, 6, 4, 14, 15, 16, 12, 18, 13, 20, 21, 22, 23],
        'B': [5, 7, 2, 3, 4, 15, 6, 14, 8, 9, 10, 11, 12, 13, 16, 18, 1, 17, 0, 19, 22, 20, 23, 21],
        'R': [0, 9, 2, 11, 6, 4, 7, 5, 8, 13, 10, 15, 12, 22, 14, 20, 16, 17, 18, 19, 3, 21, 1, 23],
        'L': [23, 1, 21, 3, 4, 5, 6, 7, 0, 9, 2, 11, 8, 13, 10, 15, 18, 16, 19, 17, 20, 14, 22, 12],
    }

    MOVES = {}
    
    @classmethod
    def _init_moves(cls):
        if cls.MOVES: return
        for m, perm in cls.PERM_MOVES.items():
            cls.MOVES[m] = perm
            # Inverse permutation
            inv_perm = [0]*24
            for i, p in enumerate(perm):
                inv_perm[p] = i
            cls.MOVES[m + "'"] = inv_perm

    def __init__(self, state=None):
        self._init_moves()
        if state is None:
            self.state = tuple(i // 4 for i in range(24))
        else:
            self.state = tuple(state)

    def apply(self, move_str):
        """Returns a new CubeState after applying the move."""
        perm = self.MOVES[move_str]
        new_state = tuple(self.state[p] for p in perm)
        return CubeState(new_state)

    def is_solved(self):
        # A state is solved if every face has uniform colors
        for i in range(6):
            face_color = self.state[i*4]
            if any(self.state[i*4 + j] != face_color for j in range(1, 4)):
                return False
        return True

    def __eq__(self, other):
        return self.state == other.state

    def __hash__(self):
        return hash(self.state)
