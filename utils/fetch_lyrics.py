"""
Adapted from https://github.com/SimonIT/spotifylyrics, specifically:
 - https://github.com/SimonIT/spotifylyrics/blob/master/backend.py
 - https://github.com/SimonIT/spotifylyrics/blob/master/services.py
at commit hash b1e85508742b127e019b6f0f751dc99f4d6bddd4

Original source was released under The Unlicense (public domain, approx. no terms)
"""

import re
import functools
import dataclasses
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
            if "By RentAnAdviser.com" not in line:
                output.append(line)

    return "\n".join(output)


def get_lyrics(artist: str, title: str) -> Optional[Lyrics]:
    song = Song(artist, title)

    for service in SERVICES:
        print("trying", service.__name__)
        result = service(song)
        if result:
            lyrics, url, service_name, timed = result
            if timed:
                print("Fetched lyrics from", service_name)
                return Lyrics(song, url, filter_lyrics(lyrics))


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
def _rentanadviser(song: Song):
    service_name = "RentAnAdviser"

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

                return lrc.text, possible_text.url, service_name, True


@lyrics_service
def _megalobiz(song: Song):
    service_name = "Megalobiz"

    search_url = "https://www.megalobiz.com/search/all?%s" % parse.urlencode({
        "qry": f"{song.artist.replace('/', '')} {song.name.replace('/', '')}",
        "display": "more"
    })
    search_results = requests.get(search_url)
    soup = BeautifulSoup(search_results.text, 'html.parser')
    result_links = soup.find(id="list_entity_container").find_all("a", class_="entity_name")

    for result_link in result_links:
        lower_title = result_link.get_text().lower()
        if song.artist.replace('/', '').lower() in lower_title and song.name.replace('/', '').lower() in lower_title:
            url = f"https://www.megalobiz.com{result_link['href']}"
            possible_text = requests.get(url)
            soup = BeautifulSoup(possible_text.text, 'html.parser')

            lrc = soup.find("div", class_="lyrics_details").span.get_text()

            return lrc, possible_text.url, service_name, True

    # perform a less intensive search if we can't find an exact match
    for result_link in result_links:
        lower_title = result_link.get_text().lower()
        if song.name.replace('/', '').lower() in lower_title:
            url = f"https://www.megalobiz.com{result_link['href']}"
            possible_text = requests.get(url)
            soup = BeautifulSoup(possible_text.text, 'html.parser')

            lrc = soup.find("div", class_="lyrics_details").span.get_text()

            return lrc, possible_text.url, service_name, True


def _lyricsify(song: Song):
    # todo: this is currently protected by CloudFlare so doesn't work as expected
    service_name = "Lyricsify"

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
                    return lrc, lyrics_page.url, service_name, True
