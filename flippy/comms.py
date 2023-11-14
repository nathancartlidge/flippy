import binascii
import math
import logging
from enum import Enum
from time import sleep
from typing import Optional

from serial import Serial
import numpy as np


class Commands(Enum):
    START_TEST_PATTERN = 3
    CLEAR_SCREEN = 12
    WRITE_IMAGE = 1


class BaseSerialComms:
    """Low-level serial comms, implementing basic communication protocols"""
    def __init__(self, port: str, address: int = 0):
        if port == "MOCK":
            self._serial = None
        else:
            self._serial = Serial(port, baudrate=4800)  # todo: can this be increased?
        self._logger = logging.getLogger("Comms")
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
        packet += self._to_ascii_hex(command.value)
        packet += self._to_ascii_hex(self.address)
        # add the payload, if it exists
        if payload:
            packet += payload

        packet += b"\x03"
        packet += self._to_ascii_hex(self._checksum(packet), full_byte=True)

        if self._serial:
            self._serial.write(packet)
        else:
            self._logger.info("MOCK WRITE: %s", binascii.hexlify(packet))

    @staticmethod
    def _to_ascii_hex(value: int | bytes, full_byte: bool = False) -> bytes:
        """
        Converts an integer value (e.g. 55) into the hexadecimal representation
        (e.g. b"37") as ASCII bytes
        """
        if isinstance(value, bytes):
            return binascii.hexlify(value).upper()
        elif full_byte:
            return f"{value:02X}".encode("ASCII")
        else:
            return f"{value:X}".encode("ASCII")

    @staticmethod
    def _checksum(data: bytes) -> int:
        """calculates a two's complement checksum for a set of bytes"""
        checksum = sum(bytearray(data))
        checksum -= 0x02  # subtract start byte
        checksum = checksum & 0xFF  # clip to a single byte
        return ((checksum ^ 0xFF) + 1) & 0xFF  # compute two's complement


class SerialComms(BaseSerialComms):
    def clear(self):
        """Clears the screen and stops a test pattern (if it is running)"""
        self.execute(Commands.CLEAR_SCREEN)

    def update(self, state: np.ndarray):
        """Updates the display with a new image"""
        payload = self._image_to_packet(state)
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
            self._logger.debug("Test pattern complete, clearing")
            self.clear()

    def _image_to_packet(self, image: np.ndarray) -> bytes:
        # we store the array column-first (to make previews easier) - however,
        #  sending data requires us to structure it as (rows, columns), due to
        #  the protocol used
        image = image.T

        # step 1: get the 'full' image size - height must be a multiple of 8
        #         (as we send each line as a byte)
        (rows, columns) = image.shape
        rows_padded = math.ceil(rows / 8) * 8

        # step 2: make this image contain the same content as our target image
        image_padded = np.full((rows_padded, columns), False, dtype=bool)
        image_padded[:rows, :] = image.astype(bool)

        # step 3: convert this to bits from an array
        image_padded_bytes = np.flipud(image_padded).view(np.uint8)
        image_padded_bytes = np.packbits(image_padded_bytes, axis=0)
        image_padded_bytes = bytes(np.flipud(image_padded_bytes).flatten("F"))

        # step 4: calculate the image header size (max 1 byte)
        image_size = len(image_padded_bytes) & 0xFF

        # step 5: convert to ASCII to make it happy, combine into a packet
        packet = self._to_ascii_hex(image_size, full_byte=True)
        packet += self._to_ascii_hex(image_padded_bytes)

        return packet
