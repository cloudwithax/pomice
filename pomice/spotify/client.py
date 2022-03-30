import asyncio
import re
import itertools
import time
from base64 import b64encode

import aiohttp

try:
    import orjson
    json = orjson
except ImportError:
    import json

from .album import Album
from .exceptions import InvalidSpotifyURL, SpotifyRequestException
from .playlist import Playlist
from .track import Track
from .artist import Artist

GRANT_URL = "https://accounts.spotify.com/api/token"
REQUEST_URL = "https://api.spotify.com/v1/{type}s/{id}"
SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)"
)


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

    async def _load(self, type_: str, request_url: str, data: dict, tracks: list, other: dict = None, full: bool = False):

        async def _fetch_async(count, url):
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

        processes = []

        if type_ == 'playlist':
            if not len(tracks):
                raise SpotifyRequestException(
                    "This playlist is empty and therefore cannot be queued.")

            urls = [f"{request_url}/tracks?offset={off}"
                    for off in range(100, data['tracks']['total']+100, 100)]

            cls = Playlist(data, [])
        else:
            urls = [REQUEST_URL.format(type="album", id=album['id'])+'/tracks'
                    for album in other['items']]

            cls = Artist(data, [])


        processes = [_fetch_async(url, count)
                     for url, count in enumerate(urls, start=1)]

        try:
            await asyncio.gather(*processes) 
        except TimeoutError:
            # dont know why it TimeoutError simply happens
            # but if it does then manually waiting for each func
            for process in processes:
                try:
                    await process
                except RuntimeError:
                    continue
           
        # tracks are jumbled for huge playlists so we use this to sort it out
        tracks.sort(key=lambda i: False if isinstance(i, Track) else i[0])
        tracks = [track for track in itertools.chain(
            *tracks) if not isinstance(track, int)]
            

        cls.tracks = tracks
        if cls.total_tracks == 0: 
            # for artists i use len(tracks) so it will be zero at first
            cls.total_tracks = len(tracks)

        return cls

    async def search(self, *, query: str):
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

        if spotify_type == 'track':
            return Track(data)
        elif spotify_type == 'album':
            return Album(data)
        else:
            tracks = []
            if spotify_type == 'playlist':
                inner = [0]
                inner.extend(Track(track['track'])
                                for track in data['tracks']['items'] if track['track'])
                tracks.append(inner)

                other = None # is for artist data
            else:
                if not data.get('items'):
                    async with self.session.get(f"{request_url}/albums", headers=self._bearer_headers) as resp:
                        if resp.status != 200:
                            raise SpotifyRequestException(
                                f"Error while fetching results: {resp.status} {resp.reason}"
                            )

                        other = await resp.json(loads=json.loads)
                else:
                    other = None
            
            return await self._load(spotify_type, request_url, data, tracks, other)
