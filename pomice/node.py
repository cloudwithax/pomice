import aiohttp
import discord
import asyncio
import typing
import json
import socket
import time

from discord.ext import commands
from typing import Optional, Union
from urllib.parse import quote
from . import events
from . import exceptions
from . import objects
from . import __version__
from .utils import ExponentialBackoff, NodeStats

class Node:
    def __init__(self, pool, bot: Union[commands.Bot, discord.Client, commands.AutoShardedBot, discord.AutoShardedClient], host: str, port: int, password: str, identifier: str, **kwargs):
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

        self._bot.add_listener(self._update_handler, "on_socket_response")

    def __repr__(self):
        return f"<Pomice.node ws_uri={self._websocket_uri} rest_uri={self._rest_uri} player_count={len(self._players)}>"

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not self._websocket.closed

    @property
    async def latency(self):
        start_time = time.time()
        await self.send(op="ping")
        end_time = await self._bot.wait_for(f"node_ping")
        return (end_time - start_time) * 1000

    @property
    async def stats(self):
        await self.send(op="get-stats")
        node_stats = await self._bot.wait_for(f"node_stats")
        return node_stats

    @property
    def players(self):
        return self._players

    @property
    def bot(self):
        return self._bot

    @property
    def pool(self):
        return self._pool

    async def _update_handler(self, data: dict):
        await self._bot.wait_until_ready()

        if not data:
            return


        if data["t"] == "VOICE_SERVER_UPDATE":

            guild_id = int(data["d"]["guild_id"])
            try:
                player = self._players[guild_id]
                await player._voice_server_update(data["d"])
            except KeyError:
                return

        elif data["t"] == "VOICE_STATE_UPDATE":

            if int(data["d"]["user_id"]) != self._bot.user.id:
                return

            guild_id = int(data["d"]["guild_id"])
            try:
                player = self._players[guild_id]
                await player._voice_state_update(data["d"])
            except KeyError:
                return

        else:
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

    async def _handle_payload(self, data: dict) -> None:
        op = data.get('op', None)
        if not op:
            return

        if op == 'stats':
            self._stats = NodeStats(data)
            return

        if not (player := self._players.get(int(data['guildId']))):
            return

        if op == 'event':
            await player._dispatch_event(data)
        elif op == 'playerUpdate':
            await player._update_state(data)


    async def send(self, **data):

        if not self.available:
            raise exceptions.NodeNotAvailable(f"The node '{self.identifier}' is not currently available.")

        await self._websocket.send_str(json.dumps(data))

    def get_player(self, guild_id: int):
        return self._players.get(guild_id, None)

    async def connect(self): 
        await self._bot.wait_until_ready()

        try:
            self._websocket = await self._session.ws_connect(self._websocket_uri, headers=self._headers, heartbeat=60)
            self._task = self._bot.loop.create_task(self._listen())
            self._pool._nodes[self._identifier] = self
            self.available = True
            return self

        except aiohttp.WSServerHandshakeError:
            raise exceptions.NodeConnectionFailure(f"The password for node '{self.identifier}' is invalid.")
        except aiohttp.InvalidURL:
            raise exceptions.NodeConnectionFailure(f"The URI for node '{self.identifier}' is invalid.")
        except socket.gaierror:
            raise exceptions.NodeConnectionFailure(f"The node '{self.identifier}' failed to connect.")

    async def disconnect(self):
        for player in self.players.copy().values():
            await player.destroy()

        await self._websocket.close()
        del self._pool.nodes[self._identifier]
        self.available = False
        self._task.cancel()
        
    async def get_tracks(self, query: str, ctx: commands.Context = None):

        async with self._session.get(url=f"{self._rest_uri}/loadtracks?identifier={quote(query)}", headers={"Authorization": self._password}) as response:
            data = await response.json()

        load_type = data.get("loadType")

        if not load_type:
            raise exceptions.TrackLoadError("There was an error while trying to load this track.")

        elif load_type == "LOAD_FAILED":
            raise exceptions.TrackLoadError(f"There was an error of severity '{data['severity']}' while loading tracks.\n\n{data['cause']}")

        elif load_type == "NO_MATCHES":
            return None

        elif load_type == "PLAYLIST_LOADED":
            if ctx:
                return objects.Playlist(playlist_info=data["playlistInfo"], tracks=data["tracks"], ctx=ctx)
            else:
                return objects.Playlist(playlist_info=data["playlistInfo"], tracks=data["tracks"])

        elif load_type == "SEARCH_RESULT" or load_type == "TRACK_LOADED":
            if ctx:
                return [objects.Track(track_id=track["track"], info=track["info"], ctx=ctx) for track in data["tracks"]]
            else:
                return [objects.Track(track_id=track["track"], info=track["info"]) for track in data["tracks"]]
