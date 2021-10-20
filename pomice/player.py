import time
from typing import Any, Dict, Optional, Type, Union

import discord
from discord import Client, Guild, VoiceChannel, VoiceProtocol
from discord.ext import commands


from . import events
from .enums import SearchType
from .exceptions import TrackInvalidPosition
from .filters import Filter
from .pool import Node, NodePool
from .objects import Track
from .utils import MISSING

class BasePlayer(VoiceProtocol):
    """Base Player Class For Pomice This Class Has to Be Inherited if your are Building 
    your own Player Class, Unless you know what you are doing.
    """

    def __call__(self, client: discord.Client, channel: VoiceChannel):
        self.client: discord.Client = client
        self.channel : VoiceChannel = channel
            
        return self
    

    def __init__(self, client : Type[Client] = MISSING, channel: VoiceChannel = MISSING):

        self.client = client
        self._bot = client
        self.channel = channel
        self._guild : Guild = channel.guild

        self._node = NodePool.get_node()
        self._volume = 100
        self._paused = False
        self._is_connected = False

        self._position = 0
        self._last_position = 0
        self._last_update = 0

        self._voice_state = {}
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(bot={self._bot}, guildId={self._guild.id})>"

    @property
    def is_connected(self) -> bool:
        """Property which returns whether or not the player is connected"""
        return self._is_connected

    @property
    def is_paused(self) -> bool:
        """Property which returns whether or not the player has a track which is paused or not."""
        return self._is_connected and self._paused
    
    @property
    def node(self) -> Node:
        """Property which returns the node the player is connected to"""
        return self._node

    @property
    def guild(self) -> Guild:
        """Property which returns the guild associated with the player"""
        return self._guild

    @property
    def volume(self) -> int:
        """Property which returns the players current volume"""
        return self._volume

    @property
    def bot(self) -> Type[Client]:
        """Property which returns the bot associated with this player instance"""
        return self._bot

    async def _update_state(self, data: dict):
        state: dict = data.get("state")
        self._last_update = time.time() * 1000
        self._is_connected = state.get("connected")
        self._last_position = state.get("position")

    async def _dispatch_voice_update(self, voice_data: Dict[str, Any]):
        if {"sessionId", "event"} != self._voice_state.keys():
            return

        await self._node.send(
            op="voiceUpdate",
            guildId=str(self.guild.id),
            **voice_data
        )

    async def on_voice_server_update(self, data: dict):
        self._voice_state.update({"event": data})
        await self._dispatch_voice_update(self._voice_state)

    async def on_voice_state_update(self, data: dict):
        self._voice_state.update({"sessionId": data.get("session_id")})

        if not (channel_id := data.get("channel_id")):
            self.channel = None
            self._voice_state.clear()
            return

        self.channel = self.guild.get_channel(int(channel_id))

        if not data.get('token'):
            return

        await self._dispatch_voice_update({**self._voice_state, "event": data})

    async def _dispatch_event(self, data: dict):
        event_type = data.get("type")
        if _track := data.get("track", None):
            track = await self._node.build_track(_track)
            
        _events = {
            "TrackStartEvent" : (self, track),
            "TrackEndEvent" : (self, track, data.get("reason", None)),
            "TrackExceptionEvent" : (self, track, data.get("error", None)),
            "TrackStuckEvent" : (self, track, data.get("thresholdMs", None)),
            "WebSocketOpenEvent": (data.get("target", None), data.get("ssrc", None)),
            "WebSocketClosedEvent" : (self._guild,  data.get("reason", None), data.get("code", None))
        }
        if (event := getattr(events, event_type, None)) and (args := _events.get(event_type, None)):
            
            self.bot.dispatch(f"pomice_{event.name}", event, *args)

    async def connect(self, *, timeout: float, reconnect: bool):
        await self.guild.change_voice_state(channel=self.channel)
        self._node._players[self.guild.id] = self
        self._is_connected = True

    async def stop(self):
        """Stops a currently playing track."""
        self._current = None
        await self._node.send(op="stop", guildId=str(self.guild.id))

    async def disconnect(self, *, force: bool = False):
        await self.stop()
        await self.guild.change_voice_state(channel=None)
        self.cleanup()
        self.channel = None
        self._is_connected = False
        del self._node._players[self.guild.id]

    async def destroy(self):
        """Disconnects a player and destroys the player instance."""
        await self.disconnect()
        await self._node.send(op="destroy", guildId=str(self.guild.id))

    

class Player(BasePlayer):
    """The Default Basic Player class for Pomice.
       In order to initiate a player, you must pass it in as a cls when you connect to a channel.
       i.e: ```py
       await ctx.author.voice.channel.connect(cls=pomice.Player)
       ```
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._current: Track = None
        self._filter: Filter = None


    def __repr__(self):
        return (
            f"<Pomice.player bot={self.bot} guildId={self.guild.id} "
            f"is_connected={self.is_connected} is_playing={self.is_playing}>"
        )

    @property
    def position(self) -> float:
        """Property which returns the player's position in a track in milliseconds"""

        if not self.is_playing or not self.current:
            return 0

        if self.is_paused:
            return min(self._last_position, self.current.length)

        difference = (time.time() * 1000) - self._last_update
        position = self._last_position + difference

        if position > self.current.length:
            return 0

        return min(position, self.current.length)

    @property
    def is_playing(self) -> bool:
        """Property which returns whether or not the player is actively playing a track."""
        return self._is_connected and self.current is not None

    @property
    def current(self) -> Track:
        """Property which returns the currently playing track"""
        return self._current

    @property
    def filter(self) -> Filter:
        """Property which returns the currently applied filter, if one is applied"""
        return self._filter


    async def get_tracks(
        self,
        query: str,
        *,
        ctx: Optional[commands.Context] = None,
        search_type: SearchType = SearchType.ytsearch
    ):
        """Fetches tracks from the node's REST api to parse into Lavalink.

        If you passed in Spotify API credentials when you created the node,
        you can also pass in a Spotify URL of a playlist, album or track and it will be parsed
        accordingly.

        You can also pass in a discord.py Context object to get a
        Context object on any track you search.
        """
        return await self._node.get_tracks(query, ctx=ctx, search_type=search_type)

    async def play(self, track: Track, *, start_position: int = 0) -> Track:
        """Plays a track. If a Spotify track is passed in, it will be handled accordingly."""
        if track.spotify:
            search: Track = (await self._node.get_tracks(
                f"{track._search_type}:{track.author} - {track.title}",
                ctx=track.ctx
            ))[0]
            track.original = search

            await self._node.send(
                op="play",
                guildId=str(self.guild.id),
                track=search.track_id,
                startTime=start_position,
                endTime=search.length,
                noReplace=False
            )
        else:
            await self._node.send(
                op="play",
                guildId=str(self.guild.id),
                track=track.track_id,
                startTime=start_position,
                endTime=track.length,
                noReplace=False
            )
        self._current = track
        return self._current

    async def seek(self, position: float) -> float:
        """Seeks to a position in the currently playing track milliseconds"""

        if position < 0 or position > self.current.length:
            raise TrackInvalidPosition(
                f"Seek position must be between 0 and the track length"
            )

        await self._node.send(op="seek", guildId=str(self.guild.id), position=position)
        return self._position

    async def set_pause(self, pause: bool) -> bool:
        """Sets the pause state of the currently playing track."""
        await self._node.send(op="pause", guildId=str(self.guild.id), pause=pause)
        self._paused = pause
        return self._paused

    async def set_volume(self, volume: int) -> int:
        """Sets the volume of the player as an integer. Lavalink accepts an amount from 0 to 500."""
        await self._node.send(op="volume", guildId=str(self.guild.id), volume=volume)
        self._volume = volume
        return self._volume

    async def set_filter(self, filter: Filter) -> Filter:
        """Sets a filter of the player. Takes a pomice.Filter object.
           This will only work if you are using the development version of Lavalink.
        """
        await self._node.send(op="filters", guildId=str(self.guild.id), **filter.payload)
        await self.seek(self.position)
        self._filter = filter
        return filter
