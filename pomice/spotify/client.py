import base64
import re
import time

import aiohttp

from .album import Album
from .exceptions import SpotifyRequestException
from .playlist import Playlist
from .track import Track

GRANT_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)

class Client:
    """The base client for the Spotify module of Pomice.
       This class will do all the heavy lifting of getting all the metadata 
       for any Spotify URL you throw at it.
    """
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id: str = client_id
        self._client_secret: str = client_secret

        self.session = aiohttp.ClientSession()

        self._bearer_token: str = None
        self._expiry: int = 0
        self._auth_token = base64.b64encode(":".join((self._client_id, self._client_secret)).encode())
        self._grant_headers = {"Authorization": f"Basic {self._auth_token.decode()}"}
        self._bearer_headers = None

    async def _fetch_bearer_token(self) -> None:
        data = {"grant_type": "client_credentials"}
        async with self.session.post(GRANT_URL, data=data, headers=self._grant_headers) as resp:
            if resp.status != 200:
                raise SpotifyRequestException(f"Error: {resp.status} {resp.reason}")

            data = await resp.json()
            self._bearer_token = data["access_token"]
            self._expiry = time.time() + (int(data["expires_in"]) - 10)
            self._bearer_headers = {"Authorization": f"Bearer {self._bearer_token}"}


    async def search(self, *, query: str):
        
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        spotify_type = result.group("type")
        spotify_id = result.group("id")

        if not result:
            return SpotifyRequestException("The Spotify link provided is not valid.")

        if spotify_type == "track":
            request_url = f"https://api.spotify.com/v1/tracks/{spotify_id}"
            async with self.session.get(request_url, headers=self._bearer_headers) as resp:
                if resp.status != 200:
                    raise SpotifyRequestException(resp.status, resp.reason)

                data: dict = await resp.json()

            return Track(data)
            
        elif spotify_type == "album":
            request_url = f"https://api.spotify.com/v1/albums/{spotify_id}"

            async with self.session.get(request_url, headers=self._bearer_headers) as resp:
                if resp.status != 200:
                    raise SpotifyRequestException(resp.status, resp.reason)

                album_data: dict = await resp.json()

            return Album(album_data)

        elif spotify_type == "playlist":
            request_url = f"https://api.spotify.com/v1/playlists/{spotify_id}"
            tracks = []
            async with self.session.get(request_url, headers=self._bearer_headers) as resp:
                if resp.status != 200:
                    raise SpotifyRequestException(resp.status, resp.reason)

                playlist_data: dict = await resp.json()

            tracks += [Track(track["track"]) for track in playlist_data["tracks"]["items"]]

            next_page_url = playlist_data["tracks"]["next"]

            while next_page_url != None:    
                async with self.session.get(next_page_url, headers=self._bearer_headers) as resp:
                    if resp.status != 200:
                        raise SpotifyRequestException(resp.status, resp.reason)

                    next_page_data: dict = await resp.json()

                tracks += [Track(track["track"]) for track in next_page_data["items"]]
                next_page_url = next_page_data["next"]
                
            return Playlist(playlist_data, tracks)

            

        
    
        




