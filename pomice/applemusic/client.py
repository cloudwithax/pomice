import re
import aiohttp
import json

from .objects import *

AM_URL_REGEX = re.compile(r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^?]+)")
AM_SINGLE_IN_ALBUM_REGEX = re.compile(r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>.+)(\?i=)(?P<id2>.+)")
AM_REQ_URL = "https://api.music.apple.com/v1/catalog/{country}/{type}s/{id}"

class Client:
    """The base Apple Music client for Pomice. 
    This will do all the heavy lifting of getting tracks from Apple Music
    and translating it to a valid Lavalink track. No client auth is required here.
    """

    def __init__(self) -> None:
        self.token: str = None
        self.origin: str = None
        self.session: aiohttp.ClientSession = None
        self.headers = None


    async def request_token(self):
        self.session = aiohttp.ClientSession()
        async with self.session.get("https://music.apple.com/assets/index.919fe17f.js") as resp:
            text = await resp.text()
            result = re.search("\"(eyJ.+?)\"", text).group(1)
            self.token = result
            self.headers = {
                'Authorization': f"Bearer {result}",
                'Origin': 'https://apple.com',
            }


    async def search(self, query: str):
        if not self.token:
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
        
        print(request_url)
        
        print(self.token)

        async with self.session.get(request_url, headers=self.headers) as resp:
            print(resp.status)
            data = await resp.json()

        with open('yes.txt', 'w') as file:
            file.write(json.dumps(data))
                
        if type == "playlist":
            return Playlist(data)
            
        elif type == "album":
            return Album(data)

        elif type == "song":
            return Song(data)
            
        elif type == "artist":
            return Artist(data)
            

        

        

        await self.session.close()