import aiohttp
import re
import time
import base64


from .exceptions import SpotifyRequestException
from .album import Album
from .playlist import Playlist
from .track import Track

GRANT_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)

class Client:
    """
    The base client for the Spotify module of Pomice.
    This class will do all the heavy lifting of getting all the metadata for any Spotify URL you throw at it.
    """
    def __init__(self, client_id: str, client_secret: str) -> None:
        print("Client initialized")
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
            self._bearer_token = data['access_token']
            self._expiry = time.time() + (int(data['expires_in']) - 10)
            self._bearer_headers = {'Authorization': f'Bearer {self._bearer_token}'}


    async def search(self, *, query: str):
        
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        spotify_type = result.group('type')
        spotify_id = result.group('id')

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
            # Okay i know this looks like a mess, but hear me out, this works
            # The Spotify Web API limits how many tracks can be seen in a single request to 100
            # So we have to do some clever techniques to get all the tracks in any playlist larger than 100 songs
            # This method doesn't need to be applied to albums due to the fact that 99% of albums
            # are never more than 100 tracks (I'm looking at you, Deep Zone Project...)
        
            request_url = f"https://api.spotify.com/v1/playlists/{spotify_id}"
            # Set the offset now so we can change it when we get all the tracks
            offset = 0
            tracks = []

            # First, get the playlist data so we can get the total amount of tracks for later
            async with self.session.get(request_url, headers=self._bearer_headers) as resp:
                if resp.status != 200:
                    raise SpotifyRequestException(resp.status, resp.reason)

                playlist_data: dict = await resp.json()

            # Second, get the total amount of tracks in said playlist so we can use this to get all the tracks
            total_tracks: int = playlist_data['tracks']['total']

            # This section of code may look spammy, but trust me, it's not
            while len(tracks) < total_tracks:    
                tracks_request_url = f"https://api.spotify.com/v1/playlists/{spotify_id}/tracks?offset={offset}&limit=100"
                async with self.session.get(tracks_request_url, headers=self._bearer_headers) as resp:
                    if resp.status != 200:
                        raise SpotifyRequestException(resp.status, resp.reason)

                    playlist_track_data: dict = await resp.json()

                # This is the juicy part..
                # Add the tracks we got from the current page of results
                tracks += [Track(track['track']) for track in playlist_track_data['items']]
                # Set the offset to go to the next page
                offset += 100
                # Repeat until we have all the tracks
                
            # We have all the tracks, cast to the class for easier reading
            return Playlist(playlist_data, tracks)

            

        
    
        




