from __future__ import annotations

import asyncio
import random
import re
from typing import Dict, List, Optional, TYPE_CHECKING, Union
from urllib.parse import quote

import aiohttp
from discord import Client
from discord.ext import commands


from . import (
    __version__, 
    spotify,
    applemusic
)

from .enums import SearchType, NodeAlgorithm
from .exceptions import (
    AppleMusicNotEnabled,
    InvalidSpotifyClientAuthorization,
    LavalinkVersionIncompatible,
    NodeConnectionFailure,
    NodeCreationError,
    NodeNotAvailable,
    NoNodesAvailable,
    NodeRestException,
    TrackLoadError
)
from .filters import Filter
from .objects import Playlist, Track
from .utils import ExponentialBackoff, NodeStats, Ping

if TYPE_CHECKING:
    from .player import Player

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)"
)

DISCORD_MP3_URL_REGEX = re.compile(
    r"https?://cdn.discordapp.com/attachments/(?P<channel_id>[0-9]+)/"
    r"(?P<message_id>[0-9]+)/(?P<file>[a-zA-Z0-9_.]+)+"
)

YOUTUBE_PLAYLIST_REGEX = re.compile(
    r"(?P<video>^.*?v.*?)(?P<list>&list.*)"
)

YOUTUBE_TIMESTAMP_REGEX = re.compile(
    r"(?P<video>^.*?)(\?t|&start)=(?P<time>\d+)?.*"
)

AM_URL_REGEX = re.compile(
    r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^?]+)"
)


URL_REGEX = re.compile(
    r"https?://(?:www\.)?.+"
)



class Node:
    """The base class for a node. 
       This node object represents a Lavalink node. 
       To enable Spotify searching, pass in a proper Spotify Client ID and Spotify Client Secret
       To enable Apple music, set the "apple_music" parameter to "True"
    """

    def __init__(
        self,
        *,
        pool,
        bot: Client,
        host: str,
        port: int,
        password: str,
        identifier: str,
        secure: bool = False,
        heartbeat: int = 30,
        session: Optional[aiohttp.ClientSession] = None,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        apple_music: bool = False

    ):
        self._bot = bot
        self._host = host
        self._port = port
        self._pool = pool
        self._password = password
        self._identifier = identifier
        self._heartbeat = heartbeat
        self._secure = secure

       
        self._websocket_uri = f"{'wss' if self._secure else 'ws'}://{self._host}:{self._port}/v3/websocket"    
        self._rest_uri = f"{'https' if self._secure else 'http'}://{self._host}:{self._port}"

        self._session = session or aiohttp.ClientSession()
        self._websocket: aiohttp.ClientWebSocketResponse = None
        self._task: asyncio.Task = None

        self._session_id: str = None
        self._metadata = None
        self._available = None

        self._headers = {
            "Authorization": self._password,
            "User-Id": str(self._bot.user.id),
            "Client-Name": f"Pomice/{__version__}"
        }

        self._players: Dict[int, Player] = {}

        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret

        self._apple_music_client = None

        if self._spotify_client_id and self._spotify_client_secret:
            self._spotify_client = spotify.Client(
                self._spotify_client_id, self._spotify_client_secret
            )

        if apple_music:
            self._apple_music_client = applemusic.Client()

        self._bot.add_listener(self._update_handler, "on_socket_response")

    def __repr__(self):
        return (
            f"<Pomice.node ws_uri={self._websocket_uri} rest_uri={self._rest_uri} "
            f"player_count={len(self._players)}>"
        )

    @property
    def is_connected(self) -> bool:
        """"Property which returns whether this node is connected or not"""
        return self._websocket is not None and not self._websocket.closed


    @property
    def stats(self) -> NodeStats:
        """Property which returns the node stats."""
        return self._stats

    @property
    def players(self) -> Dict[int, Player]:
        """Property which returns a dict containing the guild ID and the player object."""
        return self._players


    @property
    def bot(self) -> Client:
        """Property which returns the discord.py client linked to this node"""
        return self._bot

    @property
    def player_count(self) -> int:
        """Property which returns how many players are connected to this node"""
        return len(self.players)

    @property
    def pool(self):
        """Property which returns the pool this node is apart of"""
        return self._pool

    @property
    def latency(self):
        """Property which returns the latency of the node"""
        return Ping(self._host, port=self._port).get_ping()

    @property
    def ping(self):
        """Alias for `Node.latency`, returns the latency of the node"""
        return self.latency


    async def _update_handler(self, data: dict):
        await self._bot.wait_until_ready()

        if not data:
            return

        if data["t"] == "VOICE_SERVER_UPDATE":
            guild_id = int(data["d"]["guild_id"])
            try:
                player = self._players[guild_id]
                await player.on_voice_server_update(data["d"])
            except KeyError:
                return

        elif data["t"] == "VOICE_STATE_UPDATE":
            if int(data["d"]["user_id"]) != self._bot.user.id:
                return

            guild_id = int(data["d"]["guild_id"])
            try:
                player = self._players[guild_id]
                await player.on_voice_state_update(data["d"])
            except KeyError:
                return

    async def _listen(self):
        backoff = ExponentialBackoff(base=7)

        while True:
            msg = await self._websocket.receive()
            if msg.type == aiohttp.WSMsgType.CLOSED:
                retry = backoff.delay()
                await asyncio.sleep(retry)
                if not self.is_connected:
                    self._bot.loop.create_task(self.connect())
            else:
                self._bot.loop.create_task(self._handle_payload(msg.json()))

    async def _handle_payload(self, data: dict):
        op = data.get("op", None)
        if not op:
            return

        if op == "stats":
            self._stats = NodeStats(data)
            return

        if op == "ready":
            self._session_id = data.get("sessionId")

        if "guildId" in data:
            if not (player := self._players.get(int(data["guildId"]))):
                return

        if op == "event":
            await player._dispatch_event(data)
        elif op == "playerUpdate":
            await player._update_state(data)

    async def send(
        self, 
        method: str, 
        path: str, 
        guild_id: Optional[Union[int, str]] = None, 
        query: Optional[str] = None, 
        data: Optional[Union[dict, str]] = None
    ):
        if not self._available:
            raise NodeNotAvailable(
                f"The node '{self._identifier}' is unavailable."
            )

        uri: str = f'{self._rest_uri}/' \
                   f'v3/' \
                   f'{path}' \
                   f'{f"/{guild_id}" if guild_id else ""}' \
                   f'{f"?{query}" if query else ""}'

        async with self._session.request(method=method, url=uri, headers={"Authorization": self._password}, json=data or {}) as resp:
            if resp.status >= 300:
                raise NodeRestException(f'Error fetching from Lavalink REST api: {resp.status} {resp.reason}')

            if method == "DELETE":
                return await resp.json(content_type=None)
           
            return await resp.json()

        

    def get_player(self, guild_id: int):
        """Takes a guild ID as a parameter. Returns a pomice Player object."""
        return self._players.get(guild_id, None)

    async def connect(self):
        """Initiates a connection with a Lavalink node and adds it to the node pool."""
        await self._bot.wait_until_ready()

        try:
            self._websocket = await self._session.ws_connect(
                self._websocket_uri, headers=self._headers, heartbeat=self._heartbeat
            )
            self._task = self._bot.loop.create_task(self._listen())
            self._available = True
            async with self._session.get(f'{self._rest_uri}/version', headers={"Authorization": self._password}) as resp:
                version: str = await resp.text()
                version = version.replace(".", "")
                if int(version) < 370:
                    raise LavalinkVersionIncompatible(
                        "The Lavalink version you're using is incompatible."
                        "Lavalink version 3.7.0 or above is required to use this library."
                    )
                
            return self

        except aiohttp.ClientConnectorError:
            raise NodeConnectionFailure(
                f"The connection to node '{self._identifier}' failed."
            )
        except aiohttp.WSServerHandshakeError:
            raise NodeConnectionFailure(
                f"The password for node '{self._identifier}' is invalid."
            )
        except aiohttp.InvalidURL:
            raise NodeConnectionFailure(
                f"The URI for node '{self._identifier}' is invalid."
            )

    async def disconnect(self):
        """Disconnects a connected Lavalink node and removes it from the node pool.
           This also destroys any players connected to the node.
        """
        for player in self.players.copy().values():
            await player.destroy()

        await self._websocket.close()
        del self._pool.nodes[self._identifier]
        self.available = False
        self._task.cancel()

    async def build_track(
        self,
        identifier: str,
        ctx: Optional[commands.Context] = None
    ) -> Track:
        """
        Builds a track using a valid track identifier

        You can also pass in a discord.py Context object to get a
        Context object on the track it builds.
        """

        async with self._session.get(
            f"{self._rest_uri}/v3/decodetrack?",
            headers={"Authorization": self._password},
            params={"track": identifier}
        ) as resp:
            if not resp.status == 200:
                raise TrackLoadError(
                    f"Failed to build track. Check if the identifier is correct and try again."
                )

            data: dict = await resp.json()
            return Track(track_id=identifier, ctx=ctx, info=data)

    async def get_tracks(
        self,
        query: str,
        *,
        ctx: Optional[commands.Context] = None,
        search_type: SearchType = SearchType.ytsearch,
        filters: Optional[List[Filter]] = None
    ):
        """Fetches tracks from the node's REST api to parse into Lavalink.

           If you passed in Spotify API credentials, you can also pass in a
           Spotify URL of a playlist, album or track and it will be parsed accordingly.

           You can pass in a discord.py Context object to get a
           Context object on any track you search.

           You may also pass in a List of filters 
           to be applied to your track once it plays.
        """

        timestamp = None

        if not URL_REGEX.match(query) and not re.match(r"(?:ytm?|sc)search:.", query):
            query = f"{search_type}:{query}"

        if filters:
            for filter in filters:
                filter.set_preload()

        
        if AM_URL_REGEX.match(query):
            if not self._apple_music_client:
                raise AppleMusicNotEnabled(
                    "You must have Apple Music functionality enabled in order to play Apple Music tracks."
                    "Please set apple_music to True in your Node class."
                )

            apple_music_results = await self._apple_music_client.search(query=query)
            if isinstance(apple_music_results, applemusic.Song):
                return [
                    Track(
                        track_id=apple_music_results.id,
                        ctx=ctx,
                        search_type=search_type,
                        apple_music=True,
                        am_track=apple_music_results,
                        filters=filters,
                        info={
                            "title": apple_music_results.name,
                            "author": apple_music_results.artists,
                            "length": apple_music_results.length,
                            "identifier": apple_music_results.id,
                            "uri": apple_music_results.url,
                            "isStream": False,
                            "isSeekable": True,
                            "position": 0,
                            "thumbnail": apple_music_results.image,
                            "isrc": apple_music_results.isrc
                        }
                    )
                ]

            tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    search_type=search_type,
                    apple_music=True,
                    am_track=track,
                    filters=filters,
                    info={
                        "title": track.name,
                        "author": track.artists,
                        "length": track.length,
                        "identifier": track.id,
                        "uri": track.url,
                        "isStream": False,
                        "isSeekable": True,
                        "position": 0,
                        "thumbnail": track.image,
                        "isrc": track.isrc
                    }
                ) for track in apple_music_results.tracks
            ]

            return Playlist(
                playlist_info={"name": apple_music_results.name, "selectedTrack": 0},
                tracks=tracks,
                ctx=ctx,
                apple_music=True,
                am_playlist=apple_music_results
            )


        elif SPOTIFY_URL_REGEX.match(query):
            if not self._spotify_client_id and not self._spotify_client_secret:
                raise InvalidSpotifyClientAuthorization(
                    "You did not provide proper Spotify client authorization credentials. "
                    "If you would like to use the Spotify searching feature, "
                    "please obtain Spotify API credentials here: https://developer.spotify.com/"
                )

            spotify_results = await self._spotify_client.search(query=query)

            if isinstance(spotify_results, spotify.Track):
                return [
                    Track(
                        track_id=spotify_results.id,
                        ctx=ctx,
                        search_type=search_type,
                        spotify=True,
                        spotify_track=spotify_results,
                        filters=filters,
                        info={
                            "title": spotify_results.name,
                            "author": spotify_results.artists,
                            "length": spotify_results.length,
                            "identifier": spotify_results.id,
                            "uri": spotify_results.uri,
                            "isStream": False,
                            "isSeekable": True,
                            "position": 0,
                            "thumbnail": spotify_results.image,
                            "isrc": spotify_results.isrc
                        }
                    )
                ]

            tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    search_type=search_type,
                    spotify=True,
                    spotify_track=track,
                    filters=filters,
                    info={
                        "title": track.name,
                        "author": track.artists,
                        "length": track.length,
                        "identifier": track.id,
                        "uri": track.uri,
                        "isStream": False,
                        "isSeekable": True,
                        "position": 0,
                        "thumbnail": track.image,
                        "isrc": track.isrc
                    }
                ) for track in spotify_results.tracks
            ]

            return Playlist(
                playlist_info={"name": spotify_results.name, "selectedTrack": 0},
                tracks=tracks,
                ctx=ctx,
                spotify=True,
                spotify_playlist=spotify_results
            )

        elif discord_url := DISCORD_MP3_URL_REGEX.match(query):
            async with self._session.get(
                url=f"{self._rest_uri}/v3/loadtracks?identifier={quote(query)}",
                headers={"Authorization": self._password}
            ) as response:
                data: dict = await response.json()

            track: dict = data["tracks"][0]
            info: dict = track.get("info")

            return [
                Track(
                    track_id=track["track"],
                    info={
                        "title": discord_url.group("file"),
                        "author": "Unknown",
                        "length": info.get("length"),
                        "uri": info.get("uri"),
                        "position": info.get("position"),
                        "identifier": info.get("identifier")
                    },
                    ctx=ctx,
                    filters=filters
                )
            ]

        else:
            # If YouTube url contains a timestamp, capture it for use later.

            if (match := YOUTUBE_TIMESTAMP_REGEX.match(query)):
                timestamp = float(match.group("time"))

            # If query is a video thats part of a playlist, get the video and queue that instead
            # (I can't tell you how much i've wanted to implement this in here)

            if (match := YOUTUBE_PLAYLIST_REGEX.match(query)):   
                query = match.group("video")
                
            async with self._session.get(
                url=f"{self._rest_uri}/v3/loadtracks?identifier={quote(query)}",
                headers={"Authorization": self._password}
            ) as response:
                data = await response.json()


        load_type = data.get("loadType")

        if not load_type:
            raise TrackLoadError("There was an error while trying to load this track.")

        elif load_type == "LOAD_FAILED":
            exception = data["exception"]
            raise TrackLoadError(f"{exception['message']} [{exception['severity']}]")

        elif load_type == "NO_MATCHES":
            return None

        elif load_type == "PLAYLIST_LOADED":
            return Playlist(
                playlist_info=data["playlistInfo"],
                tracks=data["tracks"],
                ctx=ctx
            )

        elif load_type == "SEARCH_RESULT" or load_type == "TRACK_LOADED":
            return [
                Track(
                    track_id=track["track"],
                    info=track["info"],
                    ctx=ctx,
                    filters=filters,
                    timestamp=timestamp
                )
                for track in data["tracks"]
            ]

    async def get_recommendations(self, *, query: str, ctx: Optional[commands.Context] = None):
        """
        Gets recommendations from Spotify. Query must be a valid Spotify Track URL.
        You can pass in a discord.py Context object to get a
        Context object on all tracks that get recommended.
        """
        results = await self._spotify_client.get_recommendations(query=query)
        tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    spotify=True,
                    spotify_track=track,
                    info={
                        "title": track.name,
                        "author": track.artists,
                        "length": track.length,
                        "identifier": track.id,
                        "uri": track.uri,
                        "isStream": False,
                        "isSeekable": True,
                        "position": 0,
                        "thumbnail": track.image,
                        "isrc": track.isrc
                    },
                    requester=self.bot.user
                ) for track in results
            ]

        return tracks




class NodePool:
    """The base class for the node pool.
       This holds all the nodes that are to be used by the bot.
    """

    _nodes: dict = {}

    def __repr__(self):
        return f"<Pomice.NodePool node_count={self.node_count}>"

    @property
    def nodes(self) -> Dict[str, Node]:
        """Property which returns a dict with the node identifier and the Node object."""
        return self._nodes

    @property
    def node_count(self):
        return len(self._nodes.values())

    @classmethod
    def get_best_node(cls, *, algorithm: NodeAlgorithm) -> Node:
        """Fetches the best node based on an NodeAlgorithm.
         This option is preferred if you want to choose the best node
         from a multi-node setup using either the node's latency
         or the node's voice region.

         Use NodeAlgorithm.by_ping if you want to get the best node
         based on the node's latency.


         Use NodeAlgorithm.by_players if you want to get the best node
         based on how players it has. This method will return a node with
         the least amount of players
        """
        available_nodes = [node for node in cls._nodes.values() if node._available]

        if not available_nodes:
            raise NoNodesAvailable("There are no nodes available.")

        if algorithm == NodeAlgorithm.by_ping:
            tested_nodes = {node: node.latency for node in available_nodes}
            return min(tested_nodes, key=tested_nodes.get)

        elif algorithm == NodeAlgorithm.by_players:
            tested_nodes = {node: len(node.players.keys()) for node in available_nodes}
            return min(tested_nodes, key=tested_nodes.get)
    

    @classmethod
    def get_node(cls, *, identifier: str = None) -> Node:
        """Fetches a node from the node pool using it's identifier.
           If no identifier is provided, it will choose a node at random.
        """
        available_nodes = {
            identifier: node
            for identifier, node in cls._nodes.items() if node._available
        }

        if not available_nodes:
            raise NoNodesAvailable("There are no nodes available.")

        if identifier is None:
            return random.choice(list(available_nodes.values()))

        return available_nodes.get(identifier, None)

    @classmethod
    async def create_node(
        cls,
        *,
        bot: Client,
        host: str,
        port: str,
        password: str,
        identifier: str,
        secure: bool = False,
        heartbeat: int = 30,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        apple_music: bool = False

    ) -> Node:
        """Creates a Node object to be then added into the node pool.
           For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in cls._nodes.keys():
            raise NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(
            pool=cls, bot=bot, host=host, port=port, password=password,
            identifier=identifier, secure=secure, heartbeat=heartbeat,
            spotify_client_id=spotify_client_id, 
            session=session, spotify_client_secret=spotify_client_secret,
            apple_music=apple_music
        )

        await node.connect()
        cls._nodes[node._identifier] = node
        return node
