import re
from time import sleep, monotonic
from typing import Optional
from argparse import ArgumentParser
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


LYRICS_LOADING = "LOADING"


@dataclass
class SpotifyTrack:
    title: str
    artist: str
    start_time: float
    is_playing: bool
    time_offset: float = 0.2  # 0.2 to account for ping
    lyrics: Optional[list[tuple[float, str]]] = None
    lyrics_source: Optional[str] = None
    screens: Optional[list[tuple[float, np.ndarray]]] = None

    @classmethod
    def from_track(cls, track):
        title = re.sub(r"\(.*?\)", "", track["item"]["name"])  # remove brackets
        title = re.sub(r" - .*", "", title)  # remove hyphens
        artist = track["item"]["artists"][0]["name"]
        progress = track["progress_ms"] / 1000
        start_time = monotonic() - progress
        is_playing = track["is_playing"]
        return cls(title.strip(), artist.strip(), start_time, is_playing)

    def __eq__(self, other):
        if isinstance(other, SpotifyTrack):
            if other.title == self.title:
                if other.artist == self.artist:
                    return True
        return False


class AutoLyricsDemo(LyricsDemo):
    """
    Attempt to automatically acquire lyrics from Spotify, using a bot with the capability to read the currently playing
    song.
    """
    def __init__(self, sign: Sign, comms: SerialComms, lazy: bool = False):
        super().__init__(sign, comms)

        self._text = TextRenderer(MINECRAFT, sign.shape)
        load_dotenv()
        try:
            self._auth = SpotifyOAuth(scope="user-read-currently-playing", redirect_uri="http://localhost:8080")
        except spotipy.oauth2.SpotifyOauthError:
            print("Note: You can specify SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in a .env file")
            raise
        self._spotify = spotipy.Spotify(auth_manager=self._auth)
        self._running = True

        self._lazy = lazy
        self._track: Optional[SpotifyTrack] = None

    def _spotify_watcher(self):
        self._track = None

        while self._running:
            track = self._spotify.currently_playing()
            if track:
                current_track = SpotifyTrack.from_track(track)
                if self._track != current_track:  # track has changed
                    self._track = None

                    # show the title
                    self._sign.clear()
                    for screen, text in self._text.long_text(current_track.title + " by " + current_track.artist):
                        self._sign.state = screen
                        self._sign.update()
                        sleep(1)
                    self._sign.clear()

                    # fetch the new lyrics
                    self._track = current_track
                    self._track.lyrics_source = LYRICS_LOADING
                    lyrics = get_lyrics(self._track.artist, self._track.title)
                    if lyrics:
                        self._track.screens, self._track.lyrics = self._split_into_screens(self._process_lyrics(lyrics))
                        self._track.lyrics_source = lyrics.source
                    else:
                        self._track.screens, self._track.lyrics = None, None
                        self._track.lyrics_source = None
                else:
                    # same track, but possibly different metadata
                    if abs(current_track.start_time - self._track.start_time) > 2:
                        self._track.start_time = current_track.start_time

                    if current_track.is_playing != self._track.is_playing:
                        self._track.is_playing = current_track.is_playing
            else:
                self._track = None
                if self._lazy and self._comms.is_open:
                    self._sign.clear()
                    self._comms.close()

            # fast exit
            for i in range(4):
                if self._running:
                    sleep(0.5)

    def _handle_input(self, term, timeout, index):
        # controls - allow for skipping forwards/backwards
        key = term.inkey(timeout=timeout)
        if key == ".":
            self._track.time_offset += 0.1
        elif key == ",":
            self._track.time_offset -= 0.1
        elif key.is_sequence:
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
                print(gui.term.clear())
                while True:
                    print(gui.term.home(), end="")
                    if self._track is None:
                        print(f"\n\n{gui.term.clear()}{gui.term.red}Nothing Playing{gui.term.normal}\n\n")
                        sleep(1)
                        continue

                    print(f"{gui.term.clear_eol}{gui.term.blue}Now Playing: {self._track.title} by {self._track.artist}{gui.term.normal}")

                    # get up-to-date lyrics
                    if self._track.lyrics is None:
                        if self._track.lyrics_source == LYRICS_LOADING:
                            print(f"{gui.term.clear_eos()}\n{gui.term.red}Finding Lyrics...{gui.term.normal}\n\n\n")
                        else:
                            print(f"{gui.term.clear_eos()}\n{gui.term.red}No Lyrics{gui.term.normal}\n\n\n")
                        self._sign.state = None
                        self._sign.update()
                        sleep(0.25)
                    elif not self._track.is_playing:
                        print(f"{gui.term.clear_eos()}\n{gui.term.red}Paused{gui.term.normal}\n\n\n")
                        self._sign.state = self._text.text("| |")
                        self._sign.update()
                        sleep(0.25)
                    else:
                        gui.track = self._track
                        delta = monotonic() - self._track.start_time + self._track.time_offset
                        index = gui.show(delta)
                        print(f"{gui.term.clear_eol()}{gui.term.blue}offset: {self._track.time_offset:.2f}s / source: {self._track.lyrics_source}{gui.term.normal}")

                        if 0 <= index < len(self._track.screens):
                            self._sign.state = self._track.screens[index][1]
                            self._sign.update()
                        else:
                            self._sign.state = None
                            self._sign.update()
                        self._handle_input(gui.term, 0.05, index)
        except KeyboardInterrupt:
            input("Press enter to exit...")
        finally:
            self._running = False


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("port", help="port on which screen is connected")
    parser.add_argument("width", help="width of your screen")
    parser.add_argument("height", help="height of your screen")
    parser.add_argument("--address", default=0, help="display address")
    args = parser.parse_args()

    comms = SerialComms(port=args.port, address=args.address, lazy=True)
    sign = Sign(shape=(int(args.width), int(args.height)), comms=comms)

    demo = AutoLyricsDemo(sign, comms, lazy=True)
    demo.execute()
