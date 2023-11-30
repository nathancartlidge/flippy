from time import monotonic, sleep

from demo.sample_demo import Demo

from flippy.comms import SerialComms
from flippy.sign import Sign
from flippy.text_rendering import MINECRAFT, TextRenderer

from utils.fetch_lyrics import get_lyrics, Lyrics
from utils.lyrics_gui import Track, LyricsGui


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

    def _split_into_screens(self, lyrics: list, blank: bool = True):
        timed_screens = []
        timed_lyrics = []

        for i, (t, line) in enumerate(lyrics):
            if i + 1 != len(lyrics):
                next_t = lyrics[i + 1][0]
            else:
                next_t = t + 5

            screens = self._text.long_text(line)
            for j, (screen, screen_text) in enumerate(screens):
                screen_time = t + min(5, next_t - t) * (j / len(screens))
                timed_screens.append((screen_time, screen))
                timed_lyrics.append((screen_time, screen_text))

            if blank and next_t - t > 10:
                timed_screens.append((t + 6, None))
                timed_lyrics.append((t + 6, "♫"))

        return timed_screens, timed_lyrics

    def run(self):
        """The main code of the demo"""
        lyrics = get_lyrics(self._artist, self._title)
        if lyrics is None:
            print("Unable to fetch lyrics")
            return

        screens, lyrics = self._split_into_screens(self._process_lyrics(lyrics))
        track = Track(name=self._title,
                      artist=self._artist,
                      lyrics=lyrics,
                      screens=screens)

        input("Press enter to continue...")

        gui = LyricsGui(track)
        gui.loop(self._sign)
