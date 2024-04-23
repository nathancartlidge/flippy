"""
Adapted from https://github.com/SimonIT/spotifylyrics, specifically:
 - https://github.com/SimonIT/spotifylyrics/blob/master/backend.py
 - https://github.com/SimonIT/spotifylyrics/blob/master/services.py
at commit hash b1e85508742b127e019b6f0f751dc99f4d6bddd4

Original source was released under The Unlicense (public domain, approx. no terms)
"""
import os
import re
import functools
import dataclasses
import pathlib
from typing import Optional
from urllib import parse

import requests
from unidecode import unidecode
from bs4 import BeautifulSoup

SERVICES = []
UA = "Mozilla/5.0 (Maemo; Linux armv7l; rv:10.0.1) Gecko/20100101 Firefox/10.0.1 Fennec/10.0.1"


@dataclasses.dataclass
class Song:
    artist: str
    name: str
    duration: Optional[int] = None
    album: Optional[str] = None


@dataclasses.dataclass
class Lyrics:
    song: Song
    source: str
    lyrics: str

    def __repr__(self):
        return f"Lyrics({self.song}, {self.source})"


def filter_lyrics(lyrics: str):
    """filter lyrics with a regexp"""
    # fix html in result
    lyrics = lyrics.replace("<br>", "\n")
    lyrics = lyrics.replace("<br />", "\n")

    # fix curly quotes
    lyrics = unidecode(lyrics)
    lyrics = lyrics.replace("“", "\"")
    lyrics = lyrics.replace("”", "\"")

    # filter to only timestamped lines
    lyric_pattern = re.compile(r'^\[\d{2}:\d{2}\.\d{2}].+$')
    output = []
    for line in lyrics.splitlines():
        if lyric_pattern.match(line):
            if "RentAnAdviser" not in line:
                output.append(line)

    return "\n".join(output)


def get_lyrics(artist: str, title: str, duration: Optional[int] = None, album: Optional[str] = None,
               save: bool = True) -> Optional[Lyrics]:
    song = Song(artist.strip(), title.strip(), duration=duration, album=album)

    for service in SERVICES:
        print("> trying", service.__name__.replace("_", ""))
        result = service(song)
        if result:
            lyrics, url, timed = result
            if timed:
                print("Fetched lyrics from", service.__name__.replace("_", ""), "-", url)
                filtered = filter_lyrics(lyrics)
                if save and service.__name__ != "_local":
                    save_lyrics(song, filtered)
                return Lyrics(song, url, filtered)


def save_lyrics(song: Song, lyrics: str):
    filename = "".join([x if x.isalnum() or x in (" ", "-") else "_" for x in f"{song.name} -- {song.artist}"]) + ".lrc"
    os.makedirs("lyrics", exist_ok=True)
    file = pathlib.Path("lyrics").joinpath(filename)
    with open(file, "w", encoding="utf-8") as f:
        f.write(lyrics)


def lyrics_service(_func=None, *, enabled=True):
    def _decorator_lyrics_service(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as error:
                print("%s: %s" % (func.__name__, error))
            except Exception as e:
                raise e

        if enabled:
            SERVICES.append(wrapper)
        return wrapper

    if _func is None:
        return _decorator_lyrics_service
    else:
        return _decorator_lyrics_service(_func)


@lyrics_service
def _local(song: Song):
    filename = "".join([x if x.isalnum() or x in (" ", "-") else "_" for x in f"{song.name} -- {song.artist}"]) + ".lrc"
    file = pathlib.Path("lyrics").joinpath(filename)
    if file.exists():
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            return "\n".join(f.readlines()), str(file.resolve()), True

@lyrics_service
def _lrclib(song: Song):
    if song.duration is None:
        return None
    if song.album is None:
        query_url = f"https://lrclib.net/api/get?artist_name={song.artist}&album_name=%20&track_name={song.name}&duration={song.duration}"
    else:
        query_url = f"https://lrclib.net/api/get?artist_name={song.artist}&album_name={song.album}&track_name={song.name}&duration={song.duration}"

    rq = requests.get(query_url)
    if rq.status_code == 200:
        response = rq.json()
        lyrics = response.get("syncedLyrics", None)
        if lyrics is not None:
            return lyrics, f"https://lrclib.net/api/get/{response['id']}", True


@lyrics_service
def _megalobiz(song: Song):
    search_url = "https://www.megalobiz.com/search/all?%s" % parse.urlencode({
        "qry": f"{song.artist.replace('/', '')} {song.name.replace('/', '')}",
        "display": "more"
    })
    search_results = requests.get(search_url)
    soup = BeautifulSoup(search_results.text, 'html.parser')
    results = soup.find(id="list_entity_container")
    if results:
        result_links = results.find_all("a", class_="entity_name")
    else:
        result_links = []

    for result_link in result_links:
        lower_title = result_link.get_text().lower()
        if song.artist.replace('/', '').lower() in lower_title and song.name.replace('/', '').lower() in lower_title:
            url = f"https://www.megalobiz.com{result_link['href']}"
            possible_text = requests.get(url)
            soup = BeautifulSoup(possible_text.text, 'html.parser')

            lrc = soup.find("div", class_="lyrics_details").span.get_text()

            return lrc, possible_text.url, True

    # perform a less intensive search if we can't find an exact match
    # for result_link in result_links:
    #     lower_title = result_link.get_text().lower()
    #     if song.name.replace('/', '').lower() in lower_title:
    #         url = f"https://www.megalobiz.com{result_link['href']}"
    #         possible_text = requests.get(url)
    #         soup = BeautifulSoup(possible_text.text, 'html.parser')
    #
    #         lrc = soup.find("div", class_="lyrics_details").span.get_text()
    #
    #         return lrc, possible_text.url, True


@lyrics_service
def _rentanadviser(song: Song):
    search_url = "https://www.rentanadviser.com/en/subtitles/subtitles4songs.aspx?%s" % parse.urlencode({
        "src": f"{song.artist} {song.name}"
    })
    search_results = requests.get(search_url, headers={"User-Agent": UA})
    soup = BeautifulSoup(search_results.text, 'html.parser')
    result_links = soup.find(id="tablecontainer").find_all("a")

    for result_link in result_links:
        if result_link["href"] != "subtitles4songs.aspx":
            lower_title = result_link.get_text().lower()
            if song.artist.lower() in lower_title and song.name.lower() in lower_title:
                url = f'https://www.rentanadviser.com/en/subtitles/{result_link["href"]}&type=lrc'
                possible_text = requests.get(url, headers={"User-Agent": UA})
                soup = BeautifulSoup(possible_text.text, 'html.parser')

                event_validation = soup.find(id="__EVENTVALIDATION")["value"]
                view_state = soup.find(id="__VIEWSTATE")["value"]

                lrc = requests.post(possible_text.url,
                                    {"__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnlyrics",
                                     "__EVENTVALIDATION": event_validation,
                                     "__VIEWSTATE": view_state},
                                    headers={"User-Agent": UA, "referer": possible_text.url},
                                    cookies=search_results.cookies)

                return lrc.text, possible_text.url, True


def _lyricsify(song: Song):
    # todo: this is currently protected by CloudFlare so doesn't work as expected
    search_url = "https://www.lyricsify.com/search?%s" % parse.urlencode({
        "q": f"{song.artist} {song.name}"
    })
    search_results = requests.get(search_url, headers={"User-Agent": UA})
    soup = BeautifulSoup(search_results.text, 'html.parser')

    result_container = soup.find("div", class_="sub")

    if result_container:
        result_list = result_container.find_all("div", class_="li")

        if result_list:
            for result in result_list:
                result_link = result.find("a")
                name = result_link.get_text().lower()
                if song.artist.lower() in name and song.name.lower() in name:
                    url = f"https://www.lyricsify.com{result_link['href']}?download"
                    lyrics_page = requests.get(url, headers={"User-Agent": UA})
                    soup = BeautifulSoup(lyrics_page.text, 'html.parser')

                    download_link = soup.find(id="iframe_download")["src"]
                    lrc = requests.get(download_link,
                                       cookies=lyrics_page.cookies, headers={"User-Agent": UA}).text
                    return lrc, lyrics_page.url, True
