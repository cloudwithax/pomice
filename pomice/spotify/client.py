from __future__ import annotations

import logging
import re
import time
from base64 import b64encode
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiohttp
import orjson as json

from .exceptions import InvalidSpotifyURL
from .exceptions import SpotifyRequestException
from .objects import *

__all__ = ("Client",)


GRANT_URL = "https://accounts.spotify.com/api/token"
REQUEST_URL = "https://api.spotify.com/v1/{type}s/{id}"
SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)",
)


class Client:
    """The base client for the Spotify module of Pomice.
    This class will do all the heavy lifting of getting all the metadata
    for any Spotify URL you throw at it.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id: str = client_id
        self._client_secret: str = client_secret

        self.session: aiohttp.ClientSession = None  # type: ignore

        self._bearer_token: Optional[str] = None
        self._expiry: float = 0.0
        self._auth_token = b64encode(
            f"{self._client_id}:{self._client_secret}".encode(),
        )
        self._grant_headers = {
            "Authorization": f"Basic {self._auth_token.decode()}",
        }
        self._bearer_headers: Optional[Dict] = None
        self._log = logging.getLogger(__name__)

    async def _set_session(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def _fetch_bearer_token(self) -> None:
        _data = {"grant_type": "client_credentials"}

        resp = await self.session.post(GRANT_URL, data=_data, headers=self._grant_headers)

        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error fetching bearer token: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        self._log.debug(f"Fetched Spotify bearer token successfully")

        self._bearer_token = data["access_token"]
        self._expiry = time.time() + (int(data["expires_in"]) - 10)
        self._bearer_headers = {
            "Authorization": f"Bearer {self._bearer_token}",
        }

    async def search(self, *, query: str) -> Union[Track, Album, Artist, Playlist]:
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        if not result:
            raise InvalidSpotifyURL("The Spotify link provided is not valid.")

        spotify_type = result.group("type")
        spotify_id = result.group("id")

        request_url = REQUEST_URL.format(type=spotify_type, id=spotify_id)

        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        self._log.debug(
            f"Made request to Spotify API with status {resp.status} and response {data}",
        )

        if spotify_type == "track":
            return Track(data)
        elif spotify_type == "album":
            return Album(data)
        elif spotify_type == "artist":
            resp = await self.session.get(
                f"{request_url}/top-tracks?market=US",
                headers=self._bearer_headers,
            )
            if resp.status != 200:
                raise SpotifyRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}",
                )

            track_data: dict = await resp.json(loads=json.loads)
            tracks = track_data["tracks"]
            return Artist(data, tracks)
        else:
            tracks = [
                Track(track["track"])
                for track in data["tracks"]["items"]
                if track["track"] is not None
            ]

            if not len(tracks):
                raise SpotifyRequestException(
                    "This playlist is empty and therefore cannot be queued.",
                )

            next_page_url = data["tracks"]["next"]

            while next_page_url is not None:
                resp = await self.session.get(next_page_url, headers=self._bearer_headers)
                if resp.status != 200:
                    raise SpotifyRequestException(
                        f"Error while fetching results: {resp.status} {resp.reason}",
                    )

                next_data: dict = await resp.json(loads=json.loads)

                tracks += [
                    Track(track["track"])
                    for track in next_data["items"]
                    if track["track"] is not None
                ]
                next_page_url = next_data["next"]

            return Playlist(data, tracks)

    async def get_recommendations(self, *, query: str) -> List[Track]:
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        if not result:
            raise InvalidSpotifyURL("The Spotify link provided is not valid.")

        spotify_type = result.group("type")
        spotify_id = result.group("id")

        if not spotify_type == "track":
            raise InvalidSpotifyURL(
                "The provided query is not a Spotify track.",
            )

        request_url = REQUEST_URL.format(
            type="recommendation",
            id=f"?seed_tracks={spotify_id}",
        )

        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        tracks = [Track(track) for track in data["tracks"]]

        return tracks
