from __future__ import annotations

import asyncio
import json
import random
import re
import socket
import time
from typing import Dict, Optional, TYPE_CHECKING, Union
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

from . import __version__, spotify
from .enums import SearchType
from .exceptions import (
    InvalidSpotifyClientAuthorization,
    NodeConnectionFailure,
    NodeCreationError,
    NodeNotAvailable,
    NoNodesAvailable,
    SpotifyAlbumLoadFailed,
    SpotifyPlaylistLoadFailed,
    SpotifyTrackLoadFailed,
    TrackLoadError
)
from .objects import Playlist, Track
from .utils import (
    ClientType, 
    ExponentialBackoff, 
    NodeStats, 
    NodeAlgorithims,
)

if TYPE_CHECKING:
    from .player import Player

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)

DISCORD_MP3_URL_REGEX = re.compile(
    r"https?://cdn.discordapp.com/attachments/(?P<channel_id>[0-9]+)/(?P<message_id>[0-9]+)/(?P<file>[a-zA-Z0-9_.]+)+"
)
URL_REGEX = re.compile(
    r'https?://(?:www\.)?.+'
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
        bot: ClientType,
        host: str,
        port: int,
        password: str,
        identifier: str,
        session: Optional[aiohttp.ClientSession],
        spotify_client_id: Optional[str],
        spotify_client_secret: Optional[str],

    ):
        self._bot = bot
        self._host = host
        self._port = port
        self._pool = pool
        self._password = password
        self._identifier = identifier

        self._websocket_uri = f"ws://{self._host}:{self._port}"
        self._rest_uri = f"http://{self._host}:{self._port}"

        self._session = session or aiohttp.ClientSession()
        self._websocket: aiohttp.ClientWebSocketResponse = None
        self._task: asyncio.Task = None

        self._connection_id = None
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
    async def latency(self) -> int:
        """Property which returns the latency of the node in milliseconds"""
        start_time = time.time()
        await self.send(op="ping")
        end_time = await self._bot.wait_for("node_ping")
        return (end_time - start_time) * 1000

    @property
    async def stats(self) -> NodeStats:
        """Property which returns the node stats."""
        await self.send(op="get-stats")
        node_stats = await self._bot.wait_for("node_stats")
        return node_stats

    @property
    def players(self) -> Dict[int, Player]:
        """Property which returns a dict containing the guild ID and the player object."""
        return self._players

    @property
    def bot(self) -> ClientType:
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
                f"The node '{self.identifier}' is not currently available.")
                
        await self._websocket.send_str(json.dumps(data))

    def get_player(self, guild_id: int):
        """Takes a guild ID as a parameter. Returns a pomice Player object."""
        return self._players.get(guild_id, None)

    async def connect(self):
        """Initiates a connection with a Lavalink node and adds it to the node pool."""
        await self._bot.wait_until_ready()

        try:
            self._websocket = await self._session.ws_connect(
                self._websocket_uri, headers=self._headers, heartbeat=60
            )
            self._task = self._bot.loop.create_task(self._listen())
            self._available = True
            return self
        except aiohttp.WSServerHandshakeError:
            raise NodeConnectionFailure(
                f"The password for node '{self.identifier}' is invalid."
            )
        except aiohttp.InvalidURL:
            raise NodeConnectionFailure(
                f"The URI for node '{self.identifier}' is invalid."
            )
        except socket.gaierror:
            raise NodeConnectionFailure(
                f"The node '{self.identifier}' failed to connect."
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

        async with self._session.get(f'{self._rest_uri}/decodetrack?',
                                    headers={'Authorization': self._password},
                                    params={'track': identifier}) as resp:
                                    
            data: dict = await resp.json()
            
            if not resp.status == 200:
                raise TrackLoadError(f'Failed to build track. Status: {data["status"]}, Error: {data["error"]}.'
                                      f'Check the identifier is correct and try again.')

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

            if isinstance(spotify_results, spotify.Playlist):
                tracks = [
                    Track(
                        track_id=track.id,
                        ctx=ctx,
                        search_type=search_type,
                        spotify=True,
                        info={
                            "title": track.name,
                            "author": track.artists,
                            "length": track.length,
                            "identifier": track.id,
                            "uri": track.uri,
                            "isStream": False,
                            "isSeekable": False,
                            "position": 0,
                            "thumbnail": track.image
                        },
                    ) for track in spotify_results.tracks
                ]

                return Playlist(
                    playlist_info={"name": spotify_results.name, "selectedTrack": tracks[0]},
                    tracks=tracks,
                    ctx=ctx,
                    spotify=True,
                    thumbnail=spotify_results.image,
                    uri=spotify_results.uri,
                )

            elif isinstance(spotify_results, spotify.Album):
            
                tracks = [
                    Track(
                        track_id=track.id,
                        ctx=ctx,
                        search_type=search_type,
                        spotify=True,
                        info={
                            "title": track.name,
                            "author": track.artists,
                            "length": track.length,
                            "identifier": track.id,
                            "uri": track.uri,
                            "isStream": False,
                            "isSeekable": False,
                            "position": 0,
                            "thumbnail": track.image
                        },
                    ) for track in spotify_results.tracks
                ]

                return Playlist(
                    playlist_info={"name": spotify_results.name, "selectedTrack": tracks[0]},
                    tracks=tracks,
                    ctx=ctx,
                    spotify=True,
                    thumbnail=spotify_results.image,
                    uri=spotify_results.uri,
                )


            elif isinstance(spotify_results, spotify.Track):

                return [
                    Track(
                        track_id=spotify_results.id,
                        ctx=ctx,
                        search_type=search_type,
                        spotify=True,
                        info={
                            "title": spotify_results.name,
                            "author": spotify_results.artists,
                            "length": spotify_results.length,
                            "identifier": spotify_results.id,
                            "uri": spotify_results.uri,
                            "isStream": False,
                            "isSeekable": False,
                            "position": 0,
                            "thumbnail": spotify_results.image
                        },
                    )
                ]


        elif discord_url := DISCORD_MP3_URL_REGEX.match(query):
            async with self._session.get(
                url=f"{self._rest_uri}/loadtracks?identifier={quote(query)}",
                headers={"Authorization": self._password}
            ) as response:
                data: dict = await response.json()

            track: dict = data["tracks"][0]
            info: dict = track.get('info')

            return [Track(
                track_id=track['track'],
                info={
                    "title": discord_url.group('file'),
                    "author": "Unknown",
                    "length": info.get('length'),
                    "uri": info.get('uri'),
                    "position": info.get('position'),
                    "identifier": info.get('identifier')
                },
                ctx=ctx)]

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

    # @classmethod
    # def get_node(cls, *, identifier: str = None) -> Node:
    #     """Fetches a node from the node pool using it's identifier.
    #        If no identifier is provided, it will choose a node at random.
    #     """
    #     available_nodes = {identifier: node for identifier, node in cls._nodes.items() if node._available}
    #     if not available_nodes:
    #         raise NoNodesAvailable('There are no nodes available.')

    #     if identifier is None:
    #         return random.choice(list(available_nodes.values()))

    #     return available_nodes.get(identifier, None)

    @classmethod
    def get_node(
        cls, *, 
        identifier: str = None, 
        algorithim : NodeAlgorithims = NodeAlgorithims.base, 
        args=(), **kwargs

    ) -> Node:
        """Fetches a node from the node pool using it's identifier.
           If no identifier is provided, it will choose based on the algorithim given.
           Default Algorithim returns a random Node.
        """
        available_nodes = {identifier: node for identifier, node in cls._nodes.items() if node._available}
        if not available_nodes:
            raise NoNodesAvailable('There are no nodes available.')

        if identifier is None and isinstance(algorithim, NodeAlgorithims):
            return algorithim(list(available_nodes.values()), *args, **kwargs).first

        return available_nodes.get(identifier, None)

    @classmethod
    def get_player(cls, guildId) -> Union[Player, None]:
        """Retruns the Exact Player object after Searching all the Nodes.
        """
        for node in [node for node in cls._nodes.values() if node._available]:
            if (player := node.players.get(guildId, None)):
                return player
        return None

    @classmethod
    async def create_node(
        cls,
        *,
        bot: ClientType,
        host: str,
        port: str,
        password: str,
        identifier: str,
        spotify_client_id: Optional[str],
        spotify_client_secret: Optional[str],
        session: Optional[aiohttp.ClientSession] = None,

    ) -> Node:
        """Creates a Node object to be then added into the node pool.
           For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in cls._nodes.keys():
            raise NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(
            pool=cls, bot=bot, host=host, port=port, password=password,
            identifier=identifier, spotify_client_id=spotify_client_id,
            session=session, spotify_client_secret=spotify_client_secret
        )

        await node.connect()
        cls._nodes[node._identifier] = node
        return node
