import asyncio
import json
import random
import re
import socket
import time
from typing import Optional, Type
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

from . import __version__, objects, spotify, NodePool
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
from .spotify import SpotifyException
from .utils import ExponentialBackoff, NodeStats

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)


class Node:
    """The base class for a node. 
       This node object represents a Lavalink node. 
       To enable Spotify searching, pass in a proper Spotify Client ID and Spotify Client Secret
    """

    def __init__(
        self,
        pool,
        bot: Type[commands.Bot],
        host: str,
        port: int,
        password: str,
        identifier: str,
        spotify_client_id: Optional[str],
        spotify_client_secret: Optional[str]
    ):
        self._bot = bot
        self._host = host
        self._port = port
        self._password = password
        self._identifier = identifier
        self._pool = pool

        self._websocket_uri = f"ws://{self._host}:{self._port}"
        self._rest_uri = f"http://{self._host}:{self._port}"

        self._session = aiohttp.ClientSession()
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

        self._players = {}

        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret

        if self._spotify_client_id and self._spotify_client_secret:
            self._spotify_client = spotify.Client(
                self._spotify_client_id, self._spotify_client_secret
            )
            self._spotify_http_client = spotify.HTTPClient(
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
    def players(self) -> dict:
        """Property which returns a dict containing the guild ID and the player object."""
        return self._players

    @property
    def bot(self) -> commands.Bot:
        """Property which returns the discord.py client linked to this node"""
        return self._bot

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def pool(self) -> NodePool:
        """Property which returns the node pool this node is a part of."""
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
        if not self.available:
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
            self._pool._nodes[self._identifier] = self
            self.available = True
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

    async def get_tracks(self, query: str, ctx: commands.Context = None):
        """Fetches tracks from the node's REST api to parse into Lavalink.

           If you passed in Spotify API credentials, you can also pass in a
           Spotify URL of a playlist, album or track and it will be parsed accordingly.

           You can also pass in a discord.py Context object to get a
           Context object on any track you search.
        """
        if spotify_url_check := SPOTIFY_URL_REGEX.match(query):
            if not self._spotify_client_id and not self._spotify_client_secret:
                raise InvalidSpotifyClientAuthorization(
                    "You did not provide proper Spotify client authorization credentials. "
                    "If you would like to use the Spotify searching feature, "
                    "please obtain Spotify API credentials here: https://developer.spotify.com/"
                )

            search_type = spotify_url_check.group("type")
            spotify_id = spotify_url_check.group("id")

            if search_type == "playlist":
                results = spotify.Playlist(
                    client=self._spotify_client,
                    data=await self._spotify_http_client.get_playlist(spotify_id)
                )

                try:
                    search_tracks = await results.get_all_tracks()
                    tracks = [
                        objects.Track(
                            track_id=track.id,
                            ctx=ctx,
                            spotify=True,
                            info={
                                "title": track.name or "Unknown",
                                "author": ", ".join(
                                    artist.name for artist in track.artists
                                ) or "Unknown",
                                "length": track.duration or 0,
                                "identifier": track.id or "Unknown",
                                "uri": track.url or "spotify",
                                "isStream": False,
                                "isSeekable": False,
                                "position": 0,
                                "thumbnail": track.images[0].url if track.images else None
                            },
                        ) for track in search_tracks
                    ]

                    return objects.Playlist(
                        playlist_info={"name": results.name, "selectedTrack": tracks[0]},
                        tracks=tracks,
                        ctx=ctx,
                        spotify=True,
                        thumbnail=results.images[0].url,
                        uri=results.url,
                    )

                except SpotifyException:
                    raise SpotifyPlaylistLoadFailed(
                        f"Unable to find results for {query}"
                    )

            elif search_type == "album":
                results = await self._spotify_client.get_album(spotify_id=spotify_id)

                try:
                    search_tracks = await results.get_all_tracks()
                    tracks = [
                        objects.Track(
                            track_id=track.id,
                            ctx=ctx,
                            spotify=True,
                            info={
                                "title": track.name or "Unknown",
                                "author": ", ".join(
                                    artist.name for artist in track.artists
                                ) or "Unknown",
                                "length": track.duration or 0,
                                "identifier": track.id or "Unknown",
                                "uri": track.url or "spotify",
                                "isStream": False,
                                "isSeekable": False,
                                "position": 0,
                                "thumbnail": track.images[0].url if track.images else None
                            },
                        ) for track in search_tracks
                    ]

                    return objects.Playlist(
                        playlist_info={"name": results.name, "selectedTrack": tracks[0]},
                        tracks=tracks,
                        ctx=ctx,
                        spotify=True,
                        thumbnail=results.images[0].url,
                        uri=results.url,
                    )

                except SpotifyException:
                    raise SpotifyAlbumLoadFailed(f"Unable to find results for {query}")

            elif search_type == 'track':
                try:
                    results = await self._spotify_client.get_track(spotify_id=spotify_id)

                    return [
                        objects.Track(
                            track_id=results.id,
                            ctx=ctx,
                            spotify=True,
                            info={
                                "title": results.name or "Unknown",
                                "author": ", ".join(
                                    artist.name for artist in results.artists
                                ) or "Unknown",
                                "length": results.duration or 0,
                                "identifier": results.id or "Unknown",
                                "uri": results.url or "spotify",
                                "isStream": False,
                                "isSeekable": False,
                                "position": 0,
                                "thumbnail": results.images[0].url if results.images else None
                            },
                        )
                    ]

                except SpotifyException:
                    raise SpotifyTrackLoadFailed(f"Unable to find results for {query}")

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
            raise TrackLoadError(
                f"There was an error of severity '{data['severity']}' "
                f"while loading tracks.\n\n{data['cause']}"
            )

        elif load_type == "NO_MATCHES":
            return None

        elif load_type == "PLAYLIST_LOADED":
            return objects.Playlist(
                playlist_info=data["playlistInfo"],
                tracks=data["tracks"],
                ctx=ctx
            )

        elif load_type == "SEARCH_RESULT" or load_type == "TRACK_LOADED":
            return [
                objects.Track(
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

    _nodes: dict = {}

    def __repr__(self):
        return f"<Pomice.NodePool node_count={self.node_count}>"

    @property
    def nodes(self):
        """Property which returns a dict with the node identifier and the Node object."""
        return self._nodes

    @property
    def node_count(self):
        return len(self._nodes.values())

    @classmethod
    def get_node(self, *, identifier: str = None) -> Node:
        """Fetches a node from the node pool using it's identifier.
           If no identifier is provided, it will choose a node at random.
        """
        available_nodes = {identifier: node for identifier, node in self._nodes.items()}
        if not available_nodes:
            raise NoNodesAvailable('There are no nodes available.')

        if identifier is None:
            return random.choice(list(available_nodes.values()))

        return available_nodes.get(identifier, None)

    @classmethod
    async def create_node(
        self,
        bot: Type[discord.Client],
        host: str,
        port: str,
        password: str,
        identifier: str,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None
    ) -> Node:
        """Creates a Node object to be then added into the node pool.
           For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in self._nodes.keys():
            raise NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(
            pool=self, bot=bot, host=host, port=port, password=password,
            identifier=identifier, spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret
        )

        await node.connect()
        self._nodes[node._identifier] = node
        return node
