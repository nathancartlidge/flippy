from time import monotonic, sleep

from demo.sample_demo import Demo

from flippy.comms import SerialComms
from flippy.sign import Sign
from flippy.text_rendering import MINECRAFT, TextRenderer

from utils.fetch_lyrics import get_lyrics, Lyrics


class LyricsDemo(Demo):
    def __init__(self, sign: Sign, comms: SerialComms):
        super().__init__(sign, comms)

        self._text = TextRenderer(MINECRAFT, sign.shape)
        self._title = input("Song Title: ")
        self._artist = input("Song Artist: ")

    @staticmethod
    def _process_lyrics(lyrics: Lyrics):
        return list(map(
            lambda it: (int(it[1:3]) * 60 + float(it[4:9]), it[10:]),
            lyrics.lyrics.splitlines()
        ))

    def _split_into_screens(self, lyrics: list):
        timed_screens = []
        for i, (t, line) in enumerate(lyrics):
            if i + 1 != len(lyrics):
                next_t = lyrics[i + 1][0]
            else:
                next_t = t + 5

            screens = self._text.long_text(line)
            for j, (screen, screen_text) in enumerate(screens):
                screen_time = t + min(5, next_t - t) * (j / len(screens))
                timed_screens.append((screen_time, screen))

        return timed_screens

    def run(self):
        """The main code of the demo"""
        lyrics = get_lyrics(self._artist, self._title)
        if lyrics is None:
            print("Unable to fetch lyrics")
            return

        screens = self._split_into_screens(self._process_lyrics(lyrics))

        input("Press enter to continue...")

        start_time = monotonic()
        while screens:
            delta = monotonic() - start_time
            time, screen = screens.pop(0)

            print(f"t={delta}, u={time}")
            sleep(max(0.25, time - delta))

            delta = monotonic() - start_time
            if delta - time > 0.4:
                print(f"running behind: {delta - time:.2f}s")

            if screen is None:
                self._sign.clear()
            else:
                self._sign.state = screen
                self._sign.preview()
                self._sign.update()

        sleep(5)