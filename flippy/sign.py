import logging

import numpy as np
from flippy.comms import SerialComms


class Sign:
    """Class representing a single sign"""
    def __init__(self, shape: tuple[int, int], comms: SerialComms):
        """
        :param shape: the size of the sign, in the form `(WIDTH, HEIGHT)`
        :param comms: an initialised `SerialComms` object to communicate with
                      the sign
        """
        self._logger = logging.getLogger("Sign")
        if shape[0] < shape[1]:
            self._logger.warning("Sign is taller than it is wide - "
                                 "have you specified the shape correctly?")
        self._shape = shape
        self._comms = comms
        self._state = np.full(shape, False, dtype=bool)
        self._up_to_date = False

    @property
    def shape(self):
        """The dimensions of the sign in the form `(WIDTH, HEIGHT)`"""
        return self._shape

    @property
    def state(self):
        """
        The current state of the sign in memory (as a numpy array). This may not
        reflect the current state of the sign if the property `up_to_date` is
        not true
        """
        return self._state

    @property
    def up_to_date(self):
        """
        Returns true if `state` is a match for the state of the physical sign,
        and false otherwise
        """
        return self._up_to_date

    @state.setter
    def state(self, new_state: np.ndarray, enforce_shape: bool = True):
        """
        Update the state to a new value. Note that this does not update the
        sign: you must call `update` for that
        """
        if enforce_shape and new_state.shape != self.shape:
            raise ValueError("Incorrect Shape Provided! (%d x %d) instead of (%d x %d)",
                             *new_state.shape[0:2], *self.shape)

        # if the shape does not match, try and overlay the image anyway
        min_width = min(new_state.shape[0], self.shape[0])
        min_height = min(new_state.shape[1], self.shape[1])
        new_state_subset = new_state.astype(bool)[0:min_width, 0:min_height]

        # update the state
        self._state = np.full(self.shape, False, dtype=bool)
        self._state[0:min_width, 0:min_height] = new_state_subset
        self._up_to_date = False

    def clear(self):
        """Resets the sign so that all pixels are disabled"""
        self._comms.clear()
        self._state = np.full(self.shape, False, dtype=bool)
        self._up_to_date = True

    def update(self):
        """Updates the sign to match `state`"""
        self._comms.update(self.state)
        self._up_to_date = True

    def test_pattern(self):
        """
        Starts the test pattern sequence. This will run for 15 seconds on all
        signs connected over the Comms provided
        """
        self._comms.test_pattern()

    def preview(self, inplace: bool = False, draw_box: bool = True,
                wide: bool = True):
        """Previews the state of the sign"""
        output = ""
        if inplace:
            # control code - move cursor upwards
            output_height = (self.shape[1] + 2) if draw_box else self.shape[0]
            output += "\033[A" * output_height

        if draw_box:
            output += "┌" + "─" * (2 if wide else 1) * self.shape[0] + "┐\n"

        for row in self.state.T:
            if draw_box:
                output += "│"

            for col in row:
                if wide:
                    output += ("  ", "██")[col != 0]
                else:
                    output += (" ", "█")[col != 0]

            if draw_box:
                output += "│"
            output += "\n"

        if draw_box:
            output += "└" + "─" * (2 if wide else 1) * self.shape[0] + "┘"

        print(output)
