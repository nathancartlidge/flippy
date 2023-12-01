from dataclasses import dataclass, field
from time import monotonic
from typing import Optional

import numpy as np
import blessed

from flippy.sign import Sign


@dataclass
class Track:
    name: str = ""
    artist: str = ""
    lyrics: list[tuple[float, str]] = field(default_factory=list)
    screens: list[tuple[float, np.ndarray]] = field(default_factory=list)


class LyricsGui:
    def __init__(self, track: Optional[Track]):
        self.term = blessed.Terminal()
        self._track = track

    @property
    def track(self):
        return self._track

    @track.setter
    def track(self, value):
        self._track = value

    def progress(self, time):
        end_time = self._track.lyrics[-1][0] + 5
        percentage = min(1, time / end_time)
        width = self.term.width
        time_part = f"{time: 6.1f} / {end_time: 6.1f}"
        width -= len(time_part) + 3
        blocks = percentage * width
        if blocks % 1 > 0.5:
            progress_part = "█" * int(blocks) + "▌" + " " * (width - int(blocks) - 1)
        else:
            progress_part = "█" * int(blocks) + " " * (width - int(blocks))
        return f"{progress_part} [{time_part}]"

    def get_index(self, time: float, last_index: Optional[int] = -1) -> int:
        """returns the most recent lyric (the lyric with the largest time that is *not* larger than the current time"""
        if last_index is not None and last_index >= 0:
            candidates = self._track.lyrics[last_index + 1:]
        else:
            candidates = self._track.lyrics
            last_index = -1

        for i, (t, _) in enumerate(candidates):
            if t <= time and i != len(candidates):
                last_index += 1
            else:
                return last_index

        return len(self._track.lyrics) - 1

    def lyrics(self, index: int):
        def _safe_get(i):
            return None if i < 0 or i >= len(self._track.lyrics) else self._track.lyrics[i]

        if index is None:
            return [None, None, None]
        return [_safe_get(index - 1), _safe_get(index), _safe_get(index + 1)]

    def show(self, time: float, last_index: Optional[int] = None):
        if self.track is None:
            raise ValueError()

        # reset
        print(self.progress(time))

        index = self.get_index(time, last_index)
        lyrics = self.lyrics(index)
        for i, pair in enumerate(lyrics):
            if pair:
                t, line = pair
                if i == 1:
                    print(f"{self.term.clear_eol}{self.term.white}[{t:.1f}]: {line}{self.term.normal}")
                else:
                    print(f"{self.term.clear_eol}{self.term.red}[{t:.1f}]: {line}{self.term.normal}")
            else:
                print(self.term.clear_eol)
        return index

    def loop(self, driver: Optional[Sign] = None):
        if self.track is None:
            raise ValueError()

        print(f"{self.term.blue}Now Playing: {self._track.name}{self.term.normal}\n\n\n\n")
        end_time = self._track.lyrics[-1][0] + 5
        start_time = monotonic()
        with self.term.cbreak(), self.term.hidden_cursor():
            try:
                index = -1
                while (delta := (monotonic() - start_time)) < end_time:
                    # show interface
                    print(self.term.move_up(4), end="")
                    index = self.show(delta, index)

                    # physical sign
                    if driver is not None and 0 <= index < len(self._track.screens):
                        # because the driver does efficient updates, this won't try and write to the sign every tick
                        driver.state = self._track.screens[index][1]
                        driver.update()

                    # controls - allow for skipping forwards/backwards
                    key = self.term.inkey(timeout=0.05)
                    if key.is_sequence:
                        delta = monotonic() - start_time
                        if key.code == self.term.KEY_LEFT:
                            if index == len(self._track.lyrics):
                                offset = delta - self._track.lyrics[index - 2][0]
                                start_time += offset
                                index -= 2
                            if index > 0:
                                offset = delta - self._track.lyrics[index - 1][0]
                                start_time += offset
                                index -= 1
                            elif index == 0:
                                offset = delta - self._track.lyrics[0][0]
                                start_time += offset
                        elif key.code == self.term.KEY_RIGHT:
                            if index < len(self._track.lyrics) - 2:
                                offset = delta - self._track.lyrics[index + 1][0]
                                start_time += offset

            except KeyboardInterrupt:
                return
