import time
import datetime as dt

from demo.sample_demo import Demo
from flippy.text_rendering import TextRenderer, MINECRAFT


class TextDemo(Demo):
    """Demo of displaying text on the sign"""

    def run(self):
        text = input("What text do you want to display? ")
        renderer = TextRenderer(MINECRAFT, self._sign.shape)
        self._sign.state = renderer.text(text)
        self._sign.update()
        input("Press enter to exit...")

    def cleanup(self):
        self._sign.clear()


class ClockDemo(Demo):
    """Demo of displaying the time on the sign"""

    @staticmethod
    def get_time():
        now = dt.datetime.now()
        return f"{now.hour:02}:{now.minute:02}:{now.second:02}"

    def run(self):
        renderer = TextRenderer(MINECRAFT, self._sign.shape)
        while True:
            update_time = time.monotonic()
            self._sign.state = renderer.text(self.get_time())
            self._sign.update()
            update_time = time.monotonic() - update_time
            time.sleep(1 - update_time)


class MultiTextDemo(Demo):
    """Demo of displaying long text on the sign"""

    def run(self):
        text = input("What text do you want to display? ")
        renderer = TextRenderer(MINECRAFT, self._sign.shape)
        states = renderer.long_text(text)
        for state in states:
            self._sign.state = state
            self._sign.update()
            time.sleep(0.5)
        input("Press enter to exit...")

    def cleanup(self):
        self._sign.clear()
