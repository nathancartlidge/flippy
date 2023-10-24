from abc import abstractmethod

from flippy.comms import SerialComms
from flippy.sign import Sign


class Demo:
    def __init__(self, sign: Sign, comms: SerialComms):
        self._sign = sign
        self._comms = comms

    def execute(self):
        """Execute the example"""
        try:
            self.run()
        finally:
            self.cleanup()

    @abstractmethod
    def run(self):
        """The main code of the demo"""
        ...

    @abstractmethod
    def cleanup(self):
        """Close all handlers, reset the sign to a default state"""
        ...
