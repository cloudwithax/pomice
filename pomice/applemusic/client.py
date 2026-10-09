from __future__ import annotations

import asyncio
import base64
import logging
import re
from datetime import datetime
from typing import AsyncGenerator
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiohttp
import orjson as json

from .exceptions import *
from .objects import *

__all__ = ("Client",)

AM_URL_REGEX = re.compile(
    r"https?://music\.apple\.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+?)/(?P<id>[^/?]+?)(?:/)?(?:\?.*)?$",
)
AM_SINGLE_IN_ALBUM_REGEX = re.compile(
    r"https?://music\.apple\.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^/?]+)(\?i=)(?P<id2>[^&]+)(?:&.*)?$",
)

AM_SCRIPT_REGEX = re.compile(r'<script.*?src="(/assets/index[-~].*?)"')

AM_REQ_URL = "https://api.music.apple.com/v1/catalog/{country}/{type}s/{id}"
AM_BASE_URL = "https://api.music.apple.com"


class Client:
    """The base Apple Music client for Pomice.
    This will do all the heavy lifting of getting tracks from Apple Music
    and translating it to a valid Lavalink track. No client auth is required here.
    """

    def __init__(self, *, playlist_concurrency: int = 6) -> None:
        self.expiry: datetime = datetime(1970, 1, 1)
        self.token: str = ""
        self.headers: Dict[str, str] = {}
        self.session: aiohttp.ClientSession = None  # type: ignore
        self._log = logging.getLogger(__name__)
        # Concurrency knob for parallel playlist page retrieval
        self._playlist_concurrency = max(1, playlist_concurrency)

    async def _set_session(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def request_token(self) -> None:
        # First lets get the raw response from the main page

        resp = await self.session.get("https://music.apple.com")

        if resp.status != 200:
            raise AppleMusicRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        # Looking for script tag that fits criteria

        text = await resp.text()
        match = re.search(AM_SCRIPT_REGEX, text)

        if not match:
            raise AppleMusicRequestException(
                "Could not find valid script URL in response.",
            )

        # Found the script file, lets grab our token

        result = match.group(1)
        asset_url = result

        resp = await self.session.get("https://music.apple.com" + asset_url)

        if resp.status != 200:
            raise AppleMusicRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        text = await resp.text()
        match = re.search('"(eyJ.+?)"', text)
        if not match:
            raise AppleMusicRequestException(
                "Could not find token in response.",
            )
        result = match.group(1)

        self.token = result
        self.headers = {
            "Authorization": f"Bearer {result}",
            "Origin": "https://apple.com",
        }
        token_split = self.token.split(".")[1]
        token_json = base64.b64decode(
            token_split + "=" * (-len(token_split) % 4),
        ).decode()
        token_data = json.loads(token_json)
        self.expiry = datetime.fromtimestamp(token_data["exp"])
        if self._log:
            self._log.debug(f"Fetched Apple Music bearer token successfully")

    async def search(self, query: str) -> Union[Album, Playlist, Song, Artist]:
        if not self.token or datetime.utcnow() > self.expiry:
            await self.request_token()

        result = AM_URL_REGEX.match(query)
        if not result:
            raise InvalidAppleMusicURL(
                "The Apple Music link provided is not valid.",
            )

        country = result.group("country")
        type = result.group("type")
        id = result.group("id")

        if type == "album" and (sia_result := AM_SINGLE_IN_ALBUM_REGEX.match(query)):
            # apple music likes to generate links for singles off an album
            # by adding a param at the end of the url
            # so we're gonna scan for that and correct it
            id = sia_result.group("id2")
            type = "song"
            request_url = AM_REQ_URL.format(country=country, type=type, id=id)
        else:
            request_url = AM_REQ_URL.format(country=country, type=type, id=id)

        resp = await self.session.get(request_url, headers=self.headers)

        if resp.status != 200:
            raise AppleMusicRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        if self._log:
            self._log.debug(
                f"Made request to Apple Music API with status {resp.status} and response {data}",
            )

        data = data["data"][0]

        if type == "song":
            return Song(data)

        elif type == "album":
            return Album(data)

        elif type == "artist":
            resp = await self.session.get(
                f"{request_url}/view/top-songs",
                headers=self.headers,
            )
            if resp.status != 200:
                raise AppleMusicRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}",
                )

            top_tracks: dict = await resp.json(loads=json.loads)
            artist_tracks: dict = top_tracks["data"]

            return Artist(data, tracks=artist_tracks)
        else:
            track_data: dict = data["relationships"]["tracks"]
            album_tracks: List[Song] = [Song(track) for track in track_data["data"]]

            if not len(album_tracks):
                raise AppleMusicRequestException(
                    "This playlist is empty and therefore cannot be queued.",
                )

            # Apple Music uses cursor pagination with 'next'. We'll fetch subsequent pages
            # concurrently by first collecting cursors in rolling waves.
            next_cursor = track_data.get("next")
            semaphore = asyncio.Semaphore(self._playlist_concurrency)

            async def fetch_page(url: str) -> List[Song]:
                async with semaphore:
                    resp = await self.session.get(url, headers=self.headers)
                    if resp.status != 200:
                        if self._log:
                            self._log.warning(
                                f"Apple Music page fetch failed {resp.status} {resp.reason} for {url}",
                            )
                        return []
                    pj: dict = await resp.json(loads=json.loads)
                    songs = [Song(track) for track in pj.get("data", [])]
                    # Return songs; we will look for pj.get('next') in streaming iterator variant
                    return songs, pj.get("next")  # type: ignore

            # We'll implement a wave-based approach similar to Spotify but need to follow cursors.
            # Because we cannot know all cursors upfront, we'll iteratively fetch waves.
            waves: List[List[Song]] = []
            cursors: List[str] = []
            if next_cursor:
                cursors.append(next_cursor)

            # Limit total waves to avoid infinite loops in malformed responses
            max_waves = 50
            wave_size = self._playlist_concurrency * 2
            wave_counter = 0
            while cursors and wave_counter < max_waves:
                current = cursors[:wave_size]
                cursors = cursors[wave_size:]
                tasks = [
                    fetch_page(AM_BASE_URL + cursor) for cursor in current  # type: ignore[arg-type]
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, tuple):  # (songs, next)
                        songs, nxt = res
                        if songs:
                            waves.append(songs)
                        if nxt:
                            cursors.append(nxt)
                wave_counter += 1

            for w in waves:
                album_tracks.extend(w)

            return Playlist(data, album_tracks)

    async def iter_playlist_tracks(
        self,
        *,
        query: str,
        batch_size: int = 100,
    ) -> AsyncGenerator[List[Song], None]:
        """Stream Apple Music playlist tracks in batches.

        Parameters
        ----------
        query: str
            Apple Music playlist URL.
        batch_size: int
            Logical grouping size for yielded batches.
        """
        if not self.token or datetime.utcnow() > self.expiry:
            await self.request_token()

        result = AM_URL_REGEX.match(query)
        if not result or result.group("type") != "playlist":
            raise InvalidAppleMusicURL("Provided query is not a valid Apple Music playlist URL.")

        country = result.group("country")
        playlist_id = result.group("id")
        request_url = AM_REQ_URL.format(country=country, type="playlist", id=playlist_id)
        resp = await self.session.get(request_url, headers=self.headers)
        if resp.status != 200:
            raise AppleMusicRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )
        data: dict = await resp.json(loads=json.loads)
        playlist_data = data["data"][0]
        track_data: dict = playlist_data["relationships"]["tracks"]

        first_page_tracks = [Song(track) for track in track_data["data"]]
        for i in range(0, len(first_page_tracks), batch_size):
            yield first_page_tracks[i : i + batch_size]

        next_cursor = track_data.get("next")
        semaphore = asyncio.Semaphore(self._playlist_concurrency)

        async def fetch(cursor: str) -> tuple[List[Song], Optional[str]]:
            url = AM_BASE_URL + cursor
            async with semaphore:
                r = await self.session.get(url, headers=self.headers)
                if r.status != 200:
                    if self._log:
                        self._log.warning(
                            f"Skipping Apple Music page due to {r.status} {r.reason}",
                        )
                    return [], None
                pj: dict = await r.json(loads=json.loads)
                songs = [Song(track) for track in pj.get("data", [])]
                return songs, pj.get("next")

        # Rolling waves of fetches following cursor chain
        max_waves = 50
        wave_size = self._playlist_concurrency * 2
        waves = 0
        cursors: List[str] = []
        if next_cursor:
            cursors.append(next_cursor)
        while cursors and waves < max_waves:
            current = cursors[:wave_size]
            cursors = cursors[wave_size:]
            results = await asyncio.gather(*[fetch(c) for c in current])
            for songs, nxt in results:
                if songs:
                    for j in range(0, len(songs), batch_size):
                        yield songs[j : j + batch_size]
                if nxt:
                    cursors.append(nxt)
            waves += 1
