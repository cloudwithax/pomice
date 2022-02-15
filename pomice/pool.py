from __future__ import annotations

import asyncio
import json
import random
import re
from typing import Dict, Optional, TYPE_CHECKING
from urllib.parse import quote

import aiohttp
from discord import Client, VoiceRegion
from discord.ext import commands


from . import (
    __version__, 
    spotify,
)

from .enums import SearchType, NodeAlgorithm
from .exceptions import (
    InvalidSpotifyClientAuthorization,
    NodeConnectionFailure,
    NodeCreationError,
    NodeException,
    NodeNotAvailable,
    NoNodesAvailable,
    TrackLoadError
)
from .objects import Playlist, Track
from .utils import ExponentialBackoff, NodeStats, Ping

if TYPE_CHECKING:
    from .player import Player

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)

DISCORD_MP3_URL_REGEX = re.compile(
    r"https?://cdn.discordapp.com/attachments/(?P<channel_id>[0-9]+)/"
    r"(?P<message_id>[0-9]+)/(?P<file>[a-zA-Z0-9_.]+)+"
)

URL_REGEX = re.compile(
    r"https?://(?:www\.)?.+"
)



class Node:
    """The base class for a node. 
       This node object represents a Lavalink node. 
       To enable Spotify searching, pass in a proper Spotify Client ID and Spotify Client Secret
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
        region: Optional[VoiceRegion] = None,
        session: Optional[aiohttp.ClientSession] = None,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,

    ):
        self._bot = bot
        self._host = host
        self._port = port
        self._pool = pool
        self._password = password
        self._identifier = identifier
        self._heartbeat = heartbeat
        self._secure = secure
        self._region: Optional[VoiceRegion] = region

       
        self._websocket_uri = f"{'wss' if self._secure else 'ws'}://{self._host}:{self._port}"    
        self._rest_uri = f"{'https' if self._secure else 'http'}://{self._host}:{self._port}"

        self._session = session or aiohttp.ClientSession()
        self._websocket: aiohttp.ClientWebSocketResponse = None
        self._task: asyncio.Task = None

        self._connection_id = None
        self._metadata = None
        self._available = None

        self._headers = {
            "Authorization": self._password,
            "User-Id": str(self._bot.user.id),
            "Client-Name": f"Pomice/{__version__}",
            "Num-Shards": str(getattr(bot, "shards", 1)),
        }

        self._players: Dict[int, Player] = {}

        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret

        if self._spotify_client_id and self._spotify_client_secret:
            self._spotify_client = spotify.Client(
                self._spotify_client_id, self._spotify_client_secret
            )

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
    def region(self) -> Optional[VoiceRegion]:
        """Property which returns the VoiceRegion of the node, if one is set"""
        return self._region

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

        if not (player := self._players.get(int(data["guildId"]))):
            return

        if op == "event":
            await player._dispatch_event(data)
        elif op == "playerUpdate":
            await player._update_state(data)

    async def send(self, **data):
        if not self._available:
            raise NodeNotAvailable(
                f"The node '{self._identifier}' is unavailable."
            )

        await self._websocket.send_str(json.dumps(data))

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
            f"{self._rest_uri}/decodetrack?",
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
        search_type: SearchType = SearchType.ytsearch
    ):
        """Fetches tracks from the node's REST api to parse into Lavalink.

           If you passed in Spotify API credentials, you can also pass in a
           Spotify URL of a playlist, album or track and it will be parsed accordingly.

           You can also pass in a discord.py Context object to get a
           Context object on any track you search.
        """

        if not URL_REGEX.match(query) and not re.match(r"(?:ytm?|sc)search:.", query):
            query = f"{search_type}:{query}"

        if SPOTIFY_URL_REGEX.match(query):
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
                        info={
                            "title": spotify_results.name,
                            "author": spotify_results.artists,
                            "length": spotify_results.length,
                            "identifier": spotify_results.id,
                            "uri": spotify_results.uri,
                            "isStream": False,
                            "isSeekable": True,
                            "position": 0,
                            "thumbnail": spotify_results.image
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
                    info={
                        "title": track.name,
                        "author": track.artists,
                        "length": track.length,
                        "identifier": track.id,
                        "uri": track.uri,
                        "isStream": False,
                        "isSeekable": True,
                        "position": 0,
                        "thumbnail": track.image
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
                url=f"{self._rest_uri}/loadtracks?identifier={quote(query)}",
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
                    ctx=ctx
                )
            ]

        else:
            async with self._session.get(
                url=f"{self._rest_uri}/loadtracks?identifier={quote(query)}",
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
                    ctx=ctx
                )
                for track in data["tracks"]
            ]




class NodePool:
    """The base class for the node pool.
       This holds all the nodes that are to be used by the bot.
    """

    _nodes = {}

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
    def get_best_node(cls, *, algorithm: NodeAlgorithm, voice_region: VoiceRegion = None) -> Node:
        """Fetches the best node based on an NodeAlgorithm.
         This option is preferred if you want to choose the best node
         from a multi-node setup using either the node's latency
         or the node's voice region.

         Use NodeAlgorithm.by_ping if you want to get the best node
         based on the node's latency.

         Use NodeAlgorithm.by_region if you want to get the best node
         based on the node's voice region. This method will only work
         if you set a voice region when you create a node.

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
            
        else:
            if voice_region == None:
                raise NodeException("You must specify a VoiceRegion in order to use this functionality.")

            nodes = [node for node in available_nodes if node._region is voice_region]
            if not nodes:
                raise NoNodesAvailable(
                    f"No nodes for region {voice_region} exist in this pool."
                )

            return nodes[0] 

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
        region: Optional[VoiceRegion] = None,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,

    ) -> Node:
        """Creates a Node object to be then added into the node pool.
           For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in cls._nodes.keys():
            raise NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(
            pool=cls, bot=bot, host=host, port=port, password=password,
            identifier=identifier, secure=secure, heartbeat=heartbeat,
            region=region, spotify_client_id=spotify_client_id, 
            session=session, spotify_client_secret=spotify_client_secret
        )

        await node.connect()
        cls._nodes[node._identifier] = node
        return node
