import time
from collections import deque

import numpy as np

from demo.sample_demo import Demo


class LifeDemo(Demo):
    @staticmethod
    def step(board: np.ndarray):
        new_board = np.full(board.shape, 0)
        for i in range(board.shape[0]):
            for j in range(board.shape[1]):
                il = i - 1
                ih = (i + 1) % board.shape[0]
                jl = j - 1
                jh = (j + 1) % board.shape[1]
                neighbours = board[il, jl] + board[i, jl] + board[ih, jl] + board[il, j] + board[ih, j] + \
                    board[il, jh] + board[i, jh] + board[ih, jh]
                new_board[i, j] = (board[i, j] and neighbours in (2, 3)) or (not board[i, j] and neighbours == 3)

        return new_board

    def run(self):
        past_boards = deque(maxlen=5)
        board = np.random.random(self._sign.shape).round()

        while hash(board.data.tobytes()) not in past_boards:
            past_boards.append(hash(board.data.tobytes()))

            board = self.step(board)
            self._sign.state = board
            start_update = time.monotonic()
            self._sign.update()
            update_time = time.monotonic() - start_update
            time.sleep(max(0.3, 0.75 - update_time))
        input("Press enter to continue...")

    def cleanup(self):
        self._sign.clear()
