import re
from time import sleep, monotonic
from typing import Optional
from threading import Thread
from dataclasses import dataclass

import spotipy
import numpy as np
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from demo.lyrics import LyricsDemo

from flippy.sign import Sign
from flippy.comms import SerialComms
from flippy.text_rendering import MINECRAFT, TextRenderer

from utils.lyrics_gui import LyricsGui
from utils.fetch_lyrics import get_lyrics


@dataclass
class SpotifyTrack:
    title: str
    artist: str
    start_time: float
    is_playing: bool
    time_offset: float = 0.2  # 0.2 to account for ping
    lyrics: Optional[list[tuple[float, str]]] = None
    screens: Optional[list[tuple[float, np.ndarray]]] = None

    @classmethod
    def from_track(cls, track):
        title = re.sub(r"\(.*?\)", "", track["item"]["name"])  # remove brackets
        title = re.sub(r" - .*", "", title)  # remove hyphens
        artist = track["item"]["artists"][0]["name"]
        progress = track["progress_ms"] / 1000
        start_time = monotonic() - progress
        is_playing = track["is_playing"]
        return cls(title, artist, start_time, is_playing)

    def __eq__(self, other):
        if isinstance(other, SpotifyTrack):
            if other.title == self.title:
                if other.artist == self.artist:
                    return True
        return False


class AutoLyricsDemo(LyricsDemo):
    def __init__(self, sign: Sign, comms: SerialComms):
        super().__init__(sign, comms)

        self._text = TextRenderer(MINECRAFT, sign.shape)
        load_dotenv()
        self._auth = SpotifyOAuth(scope="user-read-currently-playing")
        self._spotify = spotipy.Spotify(auth_manager=self._auth)
        self._running = True

        self._track: Optional[SpotifyTrack] = None

    def _spotify_watcher(self):
        self._track = None

        while self._running:
            track = self._spotify.currently_playing()
            if track:
                current_track = SpotifyTrack.from_track(track)
                if self._track != current_track:
                    # track has changed, fetch the new lyrics
                    self._track = current_track
                    lyrics = get_lyrics(self._track.artist, self._track.title)
                    if lyrics:
                        self._track.screens, self._track.lyrics = self._split_into_screens(self._process_lyrics(lyrics))
                    else:
                        self._track.screens, self._track.lyrics = None, None
                else:
                    # same track, but possibly different metadata
                    if abs(current_track.start_time - self._track.start_time) > 2:
                        self._track.start_time = current_track.start_time

                    if current_track.is_playing != self._track.is_playing:
                        self._track.is_playing = current_track.is_playing
            else:
                self._track = None

            # fast exit
            for i in range(4):
                if self._running:
                    sleep(0.5)

    def _handle_input(self, term, timeout, index):
        # controls - allow for skipping forwards/backwards
        key = term.inkey(timeout=timeout)
        if key.is_sequence:
            delta = monotonic() - self._track.start_time + self._track.time_offset
            if key.code == term.KEY_LEFT:
                if index == len(self._track.lyrics):
                    offset = self._track.lyrics[index - 2][0] - delta
                    self._track.time_offset += offset
                    index -= 2
                if index > 0:
                    offset = self._track.lyrics[index - 1][0] - delta
                    self._track.time_offset += offset
                    index -= 1
                elif index == 0:
                    offset = self._track.lyrics[0][0] - delta
                    self._track.time_offset += offset
            elif key.code == term.KEY_RIGHT:
                if index < len(self._track.lyrics) - 2:
                    offset = self._track.lyrics[index + 1][0] - delta
                    self._track.time_offset += offset

    def run(self):
        """The main code of the demo"""
        spotify_watcher = Thread(target=self._spotify_watcher)
        spotify_watcher.start()
        try:
            gui = LyricsGui(None)
            with gui.term.cbreak(), gui.term.fullscreen(), gui.term.hidden_cursor():
                print("\n\n\n\n")  # clear space
                while True:
                    print(gui.term.home(), end="")
                    if self._track is None:
                        print(f"\n\n{gui.term.clear()}{gui.term.red}Nothing Playing{gui.term.normal}\n\n")
                        sleep(1)
                        continue

                    print(f"{gui.term.blue}Now Playing: {self._track.title} by {self._track.artist}{gui.term.normal}")

                    # get up-to-date lyrics
                    if self._track.lyrics is None:
                        print(f"{gui.term.clear_eos()}\n{gui.term.red}No Lyrics{gui.term.normal}\n\n")
                        self._sign.state = None
                        self._sign.update()
                        sleep(0.25)
                    elif not self._track.is_playing:
                        print(f"{gui.term.clear_eos()}\n{gui.term.red}Paused{gui.term.normal}\n\n")
                        self._sign.state = self._text.text("| |")
                        self._sign.update()
                        sleep(0.25)
                    else:
                        gui.track = self._track
                        delta = monotonic() - self._track.start_time + self._track.time_offset
                        index = gui.show(delta)
                        if 0 <= index < len(self._track.screens):
                            self._sign.state = self._track.screens[index][1]
                            self._sign.update()
                        else:
                            self._sign.state = None
                            self._sign.update()
                        self._handle_input(gui.term, 0.05, index)

        finally:
            self._running = False
