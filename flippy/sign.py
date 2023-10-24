import numpy as np
from flippy.comms import SerialComms


class Sign:
    """Class representing a single sign"""
    def __init__(self, shape: tuple[int, int], comms: SerialComms):
        self._shape = shape
        self._comms = comms
        self._state = np.full(shape, 0, dtype=np.float32)

    @property
    def shape(self):
        return self._shape

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state: np.ndarray, enforce_shape: bool = True):
        if enforce_shape and new_state.shape != self.shape:
            raise ValueError("Incorrect Shape Provided! (%d x %d) instead of (%d x %d)",
                             *new_state.shape[0:2], *self.shape)

        # reset state to zeroes
        self._state = np.full(self.shape, 0, dtype=np.float32)
        min_width = min(new_state.shape[0], self.shape[0])
        min_height = min(new_state.shape[1], self.shape[1])
        new_state_subset = new_state.astype(np.float32)[0:min_width, 0:min_height]

        self._state[0:min_width, 0:min_height] = new_state_subset

    def clear(self):
        self._state = np.full(self.shape, 0, dtype=np.float32)
        self.update()

    def update(self):
        self._comms.update(self.state)

    def test_pattern(self):
        self._comms.test_pattern()
