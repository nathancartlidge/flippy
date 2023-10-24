import math
import logging
from enum import Enum
from time import sleep
from typing import Optional

from serial import Serial
import numpy as np


class Commands(Enum):
    START_TEST_PATTERN = 3
    STOP_TEST_PATTERN = 12
    WRITE_IMAGE = 1


class BaseSerialComms:
    """Low-level serial comms, implementing basic communication protocols"""
    def __init__(self, port: str, address: int = 0):
        self._serial = Serial(port, baudrate=4800)  # todo: can this be increased?
        self._logger = logging.getLogger(self.__name__)
        self._address = address

    @property
    def address(self):
        """The target address of the connected display"""
        return self._address

    @address.setter
    def address(self, value: int):
        self._logger.debug("Updating target address to %d", value)
        if 0 <= value <= 15:
            self._address = value
        else:
            raise ValueError("Address out of range! (0..15)")

    def execute(self, command: Commands, payload: Optional[bytes] = None):
        """Executes a provided command"""
        self._logger.debug("Executing command %s", command.name)
        # add header: start byte, command, address
        packet = b"\x02"
        packet += self._int_to_ascii_hex(command.value)
        packet += self._int_to_ascii_hex(self.address)
        # add the payload, if it exists
        if payload:
            packet += payload
            packet += self._checksum(payload)
        self._serial.write(payload)

    @staticmethod
    def _int_to_ascii_hex(value: int) -> bytes:
        """
        Converts an integer value (e.g. 55) into the hexadecimal representation
        (e.g. b"37") as ASCII bytes
        """
        return hex(value)[2:].encode("ASCII")

    @staticmethod
    def _checksum(data: bytes) -> bytes:
        """calculates a two's complement checksum for a set of bytes"""
        checksum = sum(bytearray(data))
        checksum -= 0x02  # subtract start byte
        checksum = checksum & 0xFF  # clip to a single byte
        checksum = ((checksum ^ 0xFF) + 1) & 0xFF  # compute two's complement
        return bytes([checksum])


class SerialComms(BaseSerialComms):
    def update(self, state: np.ndarray):
        """Updates the display with a new image"""
        image_bytes = self._image_to_packet(state.astype(bool))
        image_size = len(image_bytes) & 0xFF
        payload = self._int_to_ascii_hex(image_size)
        self.execute(Commands.WRITE_IMAGE, payload)

    def test_pattern(self):
        """Triggers the test pattern on all displays connected on this port"""
        self._logger.debug("Starting test pattern")
        self.execute(Commands.START_TEST_PATTERN)
        try:
            sleep(15)
        except KeyboardInterrupt:
            self._logger.debug("Test pattern aborted")
        finally:
            self._logger.debug("Test pattern complete")
            self.execute(Commands.STOP_TEST_PATTERN)

    @staticmethod
    def _image_to_packet(image: np.ndarray) -> bytes:
        (rows, columns) = image.shape
        rows_padded = math.ceil(rows / 8) * 8
        output_array = np.array((rows_padded, columns), dtype=bool)
        output_array[:rows, :] = image
        output_bytes = np.packbits(np.flipud(output_array).view(np.uint8), axis=0)
        return bytes(np.flipud(output_bytes).flatten("F"))
