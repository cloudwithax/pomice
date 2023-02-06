import re
import aiohttp
import orjson as json
import base64

from datetime import datetime
from .objects import *
from .exceptions import *

AM_URL_REGEX = re.compile(r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^?]+)")
AM_SINGLE_IN_ALBUM_REGEX = re.compile(r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>.+)(\?i=)(?P<id2>.+)")
AM_REQ_URL = "https://api.music.apple.com/v1/catalog/{country}/{type}s/{id}"
AM_BASE_URL = "https://api.music.apple.com"

class Client:
    """The base Apple Music client for Pomice. 
    This will do all the heavy lifting of getting tracks from Apple Music
    and translating it to a valid Lavalink track. No client auth is required here.
    """

    def __init__(self) -> None:
        self.token: str = None
        self.expiry: datetime = None
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.headers = None


    async def request_token(self):
        async with self.session.get("https://music.apple.com/assets/index.919fe17f.js") as resp:
            if resp.status != 200:
                raise AppleMusicRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}"
                )
            text = await resp.text()
            result = re.search("\"(eyJ.+?)\"", text).group(1)
            self.token = result
            self.headers = {
                'Authorization': f"Bearer {result}",
                'Origin': 'https://apple.com',
            }
            token_split = self.token.split(".")[1]
            token_json = base64.b64decode(token_split + '=' * (-len(token_split) % 4)).decode()
            token_data = json.loads(token_json)
            self.expiry = datetime.fromtimestamp(token_data["exp"])
            

    async def search(self, query: str):
        if not self.token or datetime.utcnow() > self.expiry:
            await self.request_token()

        result = AM_URL_REGEX.match(query)

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
        

        async with self.session.get(request_url, headers=self.headers) as resp:
            if resp.status != 200:
                raise AppleMusicRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}"
                )
            data: dict = await resp.json(loads=json.loads)

        data = data["data"][0]


        if type == "song":
            return Song(data)
            
        elif type == "album":
            return Album(data)

        elif type == "artist":
            async with self.session.get(f"{request_url}/view/top-songs", headers=self.headers) as resp:
                if resp.status != 200:
                    raise AppleMusicRequestException(
                        f"Error while fetching results: {resp.status} {resp.reason}"
                    )
                top_tracks: dict = await resp.json(loads=json.loads)
                tracks: dict = top_tracks["data"]

            return Artist(data, tracks=tracks)

        else: 
            tracks = [Song(track) for track in data["relationships"]["tracks"]["data"]]

            if not len(tracks):
                raise AppleMusicRequestException("This playlist is empty and therefore cannot be queued.")

            if data["relationships"]["tracks"]["next"]:         
                next_page_url = AM_BASE_URL + data["relationships"]["tracks"]["next"]

                while next_page_url is not None:
                    async with self.session.get(next_page_url, headers=self.headers) as resp:
                        if resp.status != 200:
                            raise AppleMusicRequestException(
                                f"Error while fetching results: {resp.status} {resp.reason}"
                            )

                        next_data: dict = await resp.json(loads=json.loads)

                    tracks += [Song(track) for track in next_data["data"]]
                    if next_data.get("next"):
                        next_page_url = AM_BASE_URL + next_data["next"]
                    else:
                        next_page_url = None

            return Playlist(data, tracks)
            
            

        