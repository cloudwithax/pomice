from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING
from typing import Union
from urllib.parse import quote

import aiohttp
from discord import Client
from discord.ext import commands
from discord.utils import MISSING

from . import __version__
from . import applemusic
from . import spotify
from .enums import *
from .enums import LogLevel
from .exceptions import AppleMusicNotEnabled
from .exceptions import InvalidSpotifyClientAuthorization
from .exceptions import LavalinkVersionIncompatible
from .exceptions import NodeConnectionFailure
from .exceptions import NodeCreationError
from .exceptions import NodeNotAvailable
from .exceptions import NodeRestException
from .exceptions import NoNodesAvailable
from .exceptions import TrackLoadError
from .filters import Filter
from .objects import Playlist
from .objects import Track
from .routeplanner import RoutePlanner
from .utils import ExponentialBackoff
from .utils import LavalinkVersion
from .utils import NodeStats
from .utils import Ping

if TYPE_CHECKING:
    from .player import Player

__all__ = (
    "Node",
    "NodePool",
)


class Node:
    """The base class for a node.
    This node object represents a Lavalink node.
    To enable Spotify searching, pass in a proper Spotify Client ID and Spotify Client Secret
    To enable Apple music, set the "apple_music" parameter to "True"
    """

    __slots__ = (
        "_bot",
        "_bot_user",
        "_host",
        "_port",
        "_pool",
        "_password",
        "_identifier",
        "_heartbeat",
        "_secure",
        "_fallback",
        "_log_level",
        "_websocket_uri",
        "_rest_uri",
        "_session",
        "_websocket",
        "_task",
        "_loop",
        "_session_id",
        "_available",
        "_version",
        "_headers",
        "_players",
        "_spotify_client_id",
        "_spotify_client_secret",
        "_spotify_client",
        "_apple_music_client",
        "_route_planner",
        "_log",
        "_log_handler",
        "_stats",
        "available",
    )

    def __init__(
        self,
        *,
        pool: Type[NodePool],
        bot: commands.Bot,
        host: str,
        port: int,
        password: str,
        identifier: str,
        secure: bool = False,
        heartbeat: int = 30,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        session: Optional[aiohttp.ClientSession] = None,
        spotify_client_id: Optional[int] = None,
        spotify_client_secret: Optional[str] = None,
        apple_music: bool = False,
        fallback: bool = False,
        log_level: LogLevel = LogLevel.INFO,
        log_handler: Optional[logging.Handler] = MISSING,
    ):
        self._bot: commands.Bot = bot
        self._host: str = host
        self._port: int = port
        self._pool: Type[NodePool] = pool
        self._password: str = password
        self._identifier: str = identifier
        self._heartbeat: int = heartbeat
        self._secure: bool = secure
        self._fallback: bool = fallback
        self._log_level: LogLevel = log_level
        self._log_handler = log_handler

        self._websocket_uri: str = f"{'wss' if self._secure else 'ws'}://{self._host}:{self._port}"
        self._rest_uri: str = f"{'https' if self._secure else 'http'}://{self._host}:{self._port}"

        self._session: aiohttp.ClientSession = session  # type: ignore
        self._loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self._websocket: aiohttp.ClientWebSocketResponse
        self._task: asyncio.Task = None  # type: ignore

        self._session_id: Optional[str] = None
        self._available: bool = False
        self._version: LavalinkVersion = LavalinkVersion(0, 0, 0)

        self._route_planner = RoutePlanner(self)
        self._log = self._setup_logging(self._log_level)

        if not self._bot.user:
            raise NodeCreationError("Bot user is not ready yet.")

        self._bot_user = self._bot.user

        self._headers = {
            "Authorization": self._password,
            "User-Id": str(self._bot_user.id),
            "Client-Name": f"Pomice/{__version__}",
        }

        self._players: Dict[int, Player] = {}

        self._spotify_client_id: Optional[int] = spotify_client_id
        self._spotify_client_secret: Optional[str] = spotify_client_secret

        self._apple_music_client: Optional[applemusic.Client] = None

        if self._spotify_client_id and self._spotify_client_secret:
            self._spotify_client: spotify.Client = spotify.Client(
                self._spotify_client_id,
                self._spotify_client_secret,
            )

        if apple_music:
            self._apple_music_client = applemusic.Client()

        self._bot.add_listener(self._update_handler, "on_socket_response")

    def __repr__(self) -> str:
        return (
            f"<Pomice.node ws_uri={self._websocket_uri} rest_uri={self._rest_uri} "
            f"player_count={len(self._players)}>"
        )

    @property
    def is_connected(self) -> bool:
        """Property which returns whether this node is connected or not"""
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
    def pool(self) -> Type[NodePool]:
        """Property which returns the pool this node is apart of"""
        return self._pool

    @property
    def latency(self) -> float:
        """Property which returns the latency of the node"""
        return Ping(self._host, port=self._port).get_ping()

    @property
    def ping(self) -> float:
        """Alias for `Node.latency`, returns the latency of the node"""
        return self.latency

    def _setup_logging(self, level: LogLevel) -> logging.Logger:
        logger = logging.getLogger("pomice")
        logger.setLevel(level)
        handler = None

        if self._log_handler is not None:
            handler = self._log_handler

        elif self._log_handler is MISSING:
            handler = logging.StreamHandler()
            dt_fmt = "%Y-%m-%d %H:%M:%S"
            formatter = logging.Formatter(
                "[{asctime}] [{levelname:<8}] {name}: {message}",
                dt_fmt,
                style="{",
            )
            handler.setFormatter(formatter)

        if handler:
            logger.addHandler(handler)

        return logger

    async def _handle_version_check(self, version: str) -> None:
        if version.endswith("-SNAPSHOT"):
            # we're just gonna assume all snapshot versions correlate with v4
            self._version = LavalinkVersion(major=4, minor=0, fix=0)
            return

        # this crazy ass line maps the split version string into
        # an iterable with ints instead of strings and then
        # turns that iterable into a tuple. yeah, i know

        split = tuple(map(int, tuple(version.split("."))))
        self._version = LavalinkVersion(*split)
        if not version.endswith("-SNAPSHOT") and (
            self._version.major == 3 and self._version.minor < 7
        ):
            self._available = False
            raise LavalinkVersionIncompatible(
                "The Lavalink version you're using is incompatible. "
                "Lavalink version 3.7.0 or above is required to use this library.",
            )

    async def _update_handler(self, data: dict) -> None:
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
            if int(data["d"]["user_id"]) != self._bot_user.id:
                return

            guild_id = int(data["d"]["guild_id"])
            try:
                player = self._players[guild_id]
                await player.on_voice_state_update(data["d"])
            except KeyError:
                return

    async def _handle_node_switch(self) -> None:
        nodes = [node for node in self.pool._nodes.copy().values() if node.is_connected]
        new_node = random.choice(nodes)

        for player in self.players.copy().values():
            await player._swap_node(new_node=new_node)

        await self.disconnect()

    async def _listen(self) -> None:
        backoff = ExponentialBackoff(base=7)

        while True:
            msg = await self._websocket.receive()
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                if self._fallback:
                    await self._handle_node_switch()
                retry = backoff.delay()
                await asyncio.sleep(retry)
                if not self.is_connected:
                    self._loop.create_task(self.connect())
            else:
                self._loop.create_task(self._handle_payload(msg.json()))

    async def _handle_payload(self, data: dict) -> None:
        op = data.get("op", None)
        if not op:
            return

        if op == "stats":
            self._stats = NodeStats(data)
            return

        if op == "ready":
            self._session_id = data["sessionId"]

        if not "guildId" in data:
            return

        player = self._players.get(int(data["guildId"]))
        if not player:
            return

        if op == "event":
            await player._dispatch_event(data)
            return

        if op == "playerUpdate":
            await player._update_state(data)
            return

    async def send(
        self,
        method: str,
        path: str,
        include_version: bool = True,
        guild_id: Optional[Union[int, str]] = None,
        query: Optional[str] = None,
        data: Optional[Union[Dict, str]] = None,
        ignore_if_available: bool = False,
    ) -> Any:
        if not ignore_if_available and not self._available:
            raise NodeNotAvailable(
                f"The node '{self._identifier}' is unavailable.",
            )

        uri: str = (
            f"{self._rest_uri}/"
            f'{f"v{self._version.major}/" if include_version else ""}'
            f"{path}"
            f'{f"/{guild_id}" if guild_id else ""}'
            f'{f"?{query}" if query else ""}'
        )

        async with self._session.request(
            method=method,
            url=uri,
            headers=self._headers,
            json=data or {},
        ) as resp:
            self._log.debug(f"Making REST request with method {method} to {uri}")
            if resp.status >= 300:
                resp_data: dict = await resp.json()
                raise NodeRestException(
                    f'Error fetching from Lavalink REST api: {resp.status} {resp.reason}: {resp_data["message"]}',
                )

            if method == "DELETE" or resp.status == 204:
                self._log.debug(
                    f"REST request with method {method} to {uri} completed sucessfully and returned no data.",
                )
                return await resp.json(content_type=None)

            if resp.content_type == "text/plain":
                self._log.debug(
                    f"REST request with method {method} to {uri} completed sucessfully and returned text with body {await resp.text()}",
                )
                return await resp.text()

            self._log.debug(
                f"REST request with method {method} to {uri} completed sucessfully and returned JSON with body {await resp.json()}",
            )
            return await resp.json()

    def get_player(self, guild_id: int) -> Optional[Player]:
        """Takes a guild ID as a parameter. Returns a pomice Player object or None."""
        return self._players.get(guild_id, None)

    async def connect(self) -> "Node":
        """Initiates a connection with a Lavalink node and adds it to the node pool."""
        await self._bot.wait_until_ready()

        start = time.perf_counter()

        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            version: str = await self.send(
                method="GET",
                path="version",
                ignore_if_available=True,
                include_version=False,
            )

            await self._handle_version_check(version=version)

            self._log.debug(f"Version check from node successful. Returned version {version}")

            self._websocket = await self._session.ws_connect(
                f"{self._websocket_uri}/v{self._version.major}/websocket",
                headers=self._headers,
                heartbeat=self._heartbeat,
            )

            self._log.debug(
                f"Connected to node websocket using {self._websocket_uri}/v{self._version.major}/websocket",
            )

            if not self._task:
                self._task = self._loop.create_task(self._listen())

            self._available = True

            end = time.perf_counter()

            self._log.info(f"Connected to node {self._identifier}. Took {end - start:.3f}s")
            return self

        except (aiohttp.ClientConnectorError, ConnectionRefusedError):
            raise NodeConnectionFailure(
                f"The connection to node '{self._identifier}' failed.",
            ) from None
        except aiohttp.WSServerHandshakeError:
            raise NodeConnectionFailure(
                f"The password for node '{self._identifier}' is invalid.",
            ) from None
        except aiohttp.InvalidURL:
            raise NodeConnectionFailure(
                f"The URI for node '{self._identifier}' is invalid.",
            ) from None

    async def disconnect(self) -> None:
        """Disconnects a connected Lavalink node and removes it from the node pool.
        This also destroys any players connected to the node.
        """

        start = time.perf_counter()

        for player in self.players.copy().values():
            await player.destroy()
            self._log.debug("All players disconnected from node.")

        await self._websocket.close()
        await self._session.close()
        self._log.debug("Websocket and http session closed.")

        if self._spotify_client:
            await self._spotify_client.close()
            self._log.debug("Spotify client session closed.")

        if self._apple_music_client:
            await self._apple_music_client.close()
            self._log.debug("Apple Music client session closed.")

        del self._pool._nodes[self._identifier]
        self.available = False
        self._task.cancel()

        end = time.perf_counter()
        self._log.info(
            f"Successfully disconnected from node {self._identifier} and closed all sessions. Took {end - start:.3f}s",
        )

    async def build_track(self, identifier: str, ctx: Optional[commands.Context] = None) -> Track:
        """
        Builds a track using a valid track identifier

        You can also pass in a discord.py Context object to get a
        Context object on the track it builds.
        """

        data: dict = await self.send(
            method="GET",
            path="decodetrack",
            query=f"encodedTrack={identifier}",
        )
        return Track(
            track_id=identifier,
            ctx=ctx,
            info=data,
            track_type=TrackType(data["sourceName"]),
        )

    async def get_tracks(
        self,
        query: str,
        *,
        ctx: Optional[commands.Context] = None,
        search_type: SearchType = SearchType.ytsearch,
        filters: Optional[List[Filter]] = None,
    ) -> Optional[Union[Playlist, List[Track]]]:
        """Fetches tracks from the node's REST api to parse into Lavalink.

        If you passed in Spotify API credentials, you can also pass in a
        Spotify URL of a playlist, album or track and it will be parsed accordingly.

        You can pass in a discord.py Context object to get a
        Context object on any track you search.

        You may also pass in a List of filters
        to be applied to your track once it plays.
        """

        timestamp = None

        if not URLRegex.BASE_URL.match(query) and not re.match(r"(?:ytm?|sc)search:.", query):
            query = f"{search_type}:{query}"

        if filters:
            for filter in filters:
                filter.set_preload()

        if URLRegex.AM_URL.match(query):
            if not self._apple_music_client:
                raise AppleMusicNotEnabled(
                    "You must have Apple Music functionality enabled in order to play Apple Music tracks."
                    "Please set apple_music to True in your Node class.",
                )

            apple_music_results = await self._apple_music_client.search(query=query)
            if isinstance(apple_music_results, applemusic.Song):
                return [
                    Track(
                        track_id=apple_music_results.id,
                        ctx=ctx,
                        track_type=TrackType.APPLE_MUSIC,
                        search_type=search_type,
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
                            "isrc": apple_music_results.isrc,
                        },
                    ),
                ]

            tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    track_type=TrackType.APPLE_MUSIC,
                    search_type=search_type,
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
                        "isrc": track.isrc,
                    },
                )
                for track in apple_music_results.tracks
            ]

            return Playlist(
                playlist_info={
                    "name": apple_music_results.name,
                    "selectedTrack": 0,
                },
                tracks=tracks,
                playlist_type=PlaylistType.APPLE_MUSIC,
                thumbnail=apple_music_results.image,
                uri=apple_music_results.url,
            )

        elif URLRegex.SPOTIFY_URL.match(query):
            if not self._spotify_client_id and not self._spotify_client_secret:
                raise InvalidSpotifyClientAuthorization(
                    "You did not provide proper Spotify client authorization credentials. "
                    "If you would like to use the Spotify searching feature, "
                    "please obtain Spotify API credentials here: https://developer.spotify.com/",
                )

            spotify_results = await self._spotify_client.search(query=query)

            if isinstance(spotify_results, spotify.Track):
                return [
                    Track(
                        track_id=spotify_results.id,
                        ctx=ctx,
                        track_type=TrackType.SPOTIFY,
                        search_type=search_type,
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
                            "isrc": spotify_results.isrc,
                        },
                    ),
                ]

            tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    track_type=TrackType.SPOTIFY,
                    search_type=search_type,
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
                        "isrc": track.isrc,
                    },
                )
                for track in spotify_results.tracks
            ]

            return Playlist(
                playlist_info={
                    "name": spotify_results.name,
                    "selectedTrack": 0,
                },
                tracks=tracks,
                playlist_type=PlaylistType.SPOTIFY,
                thumbnail=spotify_results.image,
                uri=spotify_results.uri,
            )

        elif discord_url := URLRegex.DISCORD_MP3_URL.match(query):
            data: dict = await self.send(
                method="GET",
                path="loadtracks",
                query=f"identifier={quote(query)}",
            )

            track: dict = data["tracks"][0]
            info: dict = track["info"]

            return [
                Track(
                    track_id=track["track"],
                    info={
                        "title": discord_url.group("file"),
                        "author": "Unknown",
                        "length": info["length"],
                        "uri": info["uri"],
                        "position": info["position"],
                        "identifier": info["identifier"],
                    },
                    ctx=ctx,
                    track_type=TrackType.HTTP,
                    filters=filters,
                ),
            ]

        else:
            # If YouTube url contains a timestamp, capture it for use later.

            if match := URLRegex.YOUTUBE_TIMESTAMP.match(query):
                timestamp = float(match.group("time"))

            # If query is a video thats part of a playlist, get the video and queue that instead
            # (I can't tell you how much i've wanted to implement this in here)

            if match := URLRegex.YOUTUBE_VID_IN_PLAYLIST.match(query):
                query = match.group("video")

            data = await self.send(
                method="GET",
                path="loadtracks",
                query=f"identifier={quote(query)}",
            )

        load_type = data.get("loadType")

        if not load_type:
            raise TrackLoadError(
                "There was an error while trying to load this track.",
            )

        elif load_type == "LOAD_FAILED":
            exception = data["exception"]
            raise TrackLoadError(
                f"{exception['message']} [{exception['severity']}]",
            )

        elif load_type == "NO_MATCHES":
            return None

        elif load_type == "PLAYLIST_LOADED":
            tracks = [
                Track(
                    track_id=track["encoded"],
                    info=track["info"],
                    ctx=ctx,
                    track_type=TrackType(track["info"]["sourceName"]),
                )
                for track in data["tracks"]
            ]
            return Playlist(
                playlist_info=data["playlistInfo"],
                tracks=tracks,
                playlist_type=PlaylistType(tracks[0].track_type.value),
                thumbnail=tracks[0].thumbnail,
                uri=query,
            )

        elif load_type == "SEARCH_RESULT" or load_type == "TRACK_LOADED":
            return [
                Track(
                    track_id=track["encoded"],
                    info=track["info"],
                    ctx=ctx,
                    track_type=TrackType(track["info"]["sourceName"]),
                    filters=filters,
                    timestamp=timestamp,
                )
                for track in data["tracks"]
            ]

        else:
            raise TrackLoadError(
                "There was an error while trying to load this track.",
            )

    async def get_recommendations(
        self, *, track: Track, ctx: Optional[commands.Context] = None
    ) -> Optional[Union[List[Track], Playlist]]:
        """
        Gets recommendations from either YouTube or Spotify.
        The track that is passed in must be either from
        YouTube or Spotify or else this will not work.
        You can pass in a discord.py Context object to get a
        Context object on all tracks that get recommended.
        """
        if track.track_type == TrackType.SPOTIFY:
            results = await self._spotify_client.get_recommendations(query=track.uri)
            tracks = [
                Track(
                    track_id=track.id,
                    ctx=ctx,
                    track_type=TrackType.SPOTIFY,
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
                        "isrc": track.isrc,
                    },
                    requester=self.bot.user,
                )
                for track in results
            ]
            return tracks

        elif track.track_type == TrackType.YOUTUBE:
            return await self.get_tracks(
                query=f"ytsearch:https://www.youtube.com/watch?v={track.identifier}&list=RD{track.identifier}",
                ctx=ctx,
            )

        else:
            raise TrackLoadError(
                "The specfied track must be either a YouTube or Spotify track to recieve recommendations.",
            )


class NodePool:
    """The base class for the node pool.
    This holds all the nodes that are to be used by the bot.
    """

    __slots__ = ()
    _nodes: Dict[str, Node] = {}

    def __repr__(self) -> str:
        return f"<Pomice.NodePool node_count={self.node_count}>"

    @property
    def nodes(self) -> Dict[str, Node]:
        """Property which returns a dict with the node identifier and the Node object."""
        return self._nodes

    @property
    def node_count(self) -> int:
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
        available_nodes: List[Node] = [node for node in cls._nodes.values() if node._available]

        if not available_nodes:
            raise NoNodesAvailable("There are no nodes available.")

        if algorithm == NodeAlgorithm.by_ping:
            tested_nodes = {node: node.latency for node in available_nodes}
            return min(tested_nodes, key=tested_nodes.get)  # type: ignore

        elif algorithm == NodeAlgorithm.by_players:
            tested_nodes = {node: len(node.players.keys()) for node in available_nodes}
            return min(tested_nodes, key=tested_nodes.get)  # type: ignore

        else:
            raise ValueError(
                "The algorithm provided is not a valid NodeAlgorithm.",
            )

    @classmethod
    def get_node(cls, *, identifier: Optional[str] = None) -> Node:
        """Fetches a node from the node pool using it's identifier.
        If no identifier is provided, it will choose a node at random.
        """
        available_nodes = {
            identifier: node for identifier, node in cls._nodes.items() if node._available
        }

        if not available_nodes:
            raise NoNodesAvailable("There are no nodes available.")

        if identifier is None:
            return random.choice(list(available_nodes.values()))

        return available_nodes[identifier]

    @classmethod
    async def create_node(
        cls,
        *,
        bot: commands.Bot,
        host: str,
        port: int,
        password: str,
        identifier: str,
        secure: bool = False,
        heartbeat: int = 30,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        spotify_client_id: Optional[int] = None,
        spotify_client_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        apple_music: bool = False,
        fallback: bool = False,
        log_level: LogLevel = LogLevel.INFO,
        log_handler: Optional[logging.Handler] = None,
    ) -> Node:
        """Creates a Node object to be then added into the node pool.
        For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in cls._nodes.keys():
            raise NodeCreationError(
                f"A node with identifier '{identifier}' already exists.",
            )

        node = Node(
            pool=cls,
            bot=bot,
            host=host,
            port=port,
            password=password,
            identifier=identifier,
            secure=secure,
            heartbeat=heartbeat,
            loop=loop,
            spotify_client_id=spotify_client_id,
            session=session,
            spotify_client_secret=spotify_client_secret,
            apple_music=apple_music,
            fallback=fallback,
            log_level=log_level,
            log_handler=log_handler,
        )

        await node.connect()
        cls._nodes[node._identifier] = node
        return node

    @classmethod
    async def disconnect(cls) -> None:
        """Disconnects all available nodes from the node pool."""

        available_nodes: List[Node] = [node for node in cls._nodes.values() if node._available]

        for node in available_nodes:
            await node.disconnect()
