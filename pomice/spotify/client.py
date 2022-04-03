import asyncio
import itertools
import time
from base64 import b64encode

import aiohttp

try:
    import orjson
    json = orjson
except ImportError:
    import json

from typing import Union
from ...regex import SPOTIFY_URL_REGEX
from .exceptions import InvalidSpotifyURL, SpotifyRequestException
from .objects import *

GRANT_URL = "https://accounts.spotify.com/api/token"
REQUEST_URL = "https://api.spotify.com/v1/{type}s/{id}"


class Client:
    """The base client for the Spotify module of Pomice.
       This class will do all the heavy lifting of getting all the metadata 
       for any Spotify URL you throw at it.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
    ) -> None:

        self._client_id = client_id
        self._client_secret = client_secret

        self.session = aiohttp.ClientSession()

        self._bearer_token: str = None
        self._expiry = 0
        self._auth_token = b64encode(
            f"{self._client_id}:{self._client_secret}".encode())
        self._grant_headers = {
            "Authorization": f"Basic {self._auth_token.decode()}"}
        self._bearer_headers = None

    async def _fetch_bearer_token(self) -> None:
        _data = {"grant_type": "client_credentials"}

        async with self.session.post(GRANT_URL, data=_data, headers=self._grant_headers) as resp:
            if resp.status != 200:
                raise SpotifyRequestException(
                    f"Error fetching bearer token: {resp.status} {resp.reason}"
                )

            data: dict = await resp.json(loads=json.loads)

        self._bearer_token = data["access_token"]
        self._expiry = time.time() + (int(data["expires_in"]) - 10)
        self._bearer_headers = {
            "Authorization": f"Bearer {self._bearer_token}"}

    async def close(self):
        """Close Session with the Spotify API"""
        await self.session.close()

    async def search(
        self,
        *, query: str,
        raw: bool = False,
        full: bool = False
    ) -> Union[Track, Playlist, Album, Artist]:

        async def _fetch_async(count, url):
            """Internal function"""
            async with self.session.get(url, headers=self._bearer_headers) as resp:
                if resp.status != 200:
                    raise SpotifyRequestException(
                        f"Error while fetching results: {resp.status} {resp.reason}"
                    )

                next_data: dict = await resp.json(loads=json.loads)
                inner = [count]
                inner.extend(Track(track.get('track') or track)
                             for track in next_data['items'])
                tracks.append(inner)

        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        spotify_type = result.group("type")
        spotify_id = result.group("id")

        if not result:
            raise InvalidSpotifyURL("The Spotify link provided is not valid.")

        request_url = REQUEST_URL.format(type=spotify_type, id=spotify_id)

        async with self.session.get(request_url, headers=self._bearer_headers) as resp:
            if resp.status != 200:
                raise SpotifyRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}"
                )

            data = await resp.json(loads=json.loads)

        if raw:
            return data

        if spotify_type == 'track':
            return Track(data)
        elif spotify_type == 'album':
            return Album(data)
        else:
            tracks = []

            if spotify_type == 'playlist':
                # with this method of querying each task is completed at different times,
                # so this will help us sort it, since it will be jumbled.
                inner = [0]
                inner.extend(Track(track['track'])
                             for track in data['tracks']['items'] if track['track'])
                tracks.append(inner)

                if not len(tracks[0][1:]):  # not considering the first number
                    raise SpotifyRequestException(
                        "This playlist is empty and therefore cannot be queued."
                    )

                urls = [f"{request_url}/tracks?offset={off}"
                        for off in range(100, data['tracks']['total']+100, 100)]

                cls = Playlist(data, [])
            else:
                async with self.session.get(f"{request_url}/albums", headers=self._bearer_headers) as resp:
                    if resp.status != 200:
                        raise SpotifyRequestException(
                            f"Error while fetching results: {resp.status} {resp.reason}"
                        )

                    artist_data = await resp.json(loads=json.loads)

                urls = [REQUEST_URL.format(type="album", id=album['id'])+'/tracks'
                        for album in artist_data['items']]

            processes = [_fetch_async(url, count)
                         for count, url in enumerate(urls, start=1)]

            try:
                await asyncio.gather(*processes)
            except aiohttp.ClientOSError:
                for proccess in processes:
                    try:
                        await proccess
                        # if process is already awaited
                    except RuntimeError:
                        continue

            tracks.sort(key=lambda i: i[0])
            tracks = [track for track in itertools.chain(
                *tracks) if not isinstance(track, int)]

            cls.tracks = tracks
            if cls.total_tracks == 0:
                cls.total_tracks = len(tracks)
            
            return cls
