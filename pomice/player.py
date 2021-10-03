import time

import discord

from . import exceptions
from . import filters
from . import objects
from .node import Node
from .pool import NodePool
from . import events

import discord
from discord import VoiceProtocol, VoiceChannel
from discord.ext import commands
from typing import Dict, Optional, Any, Union



class Player(VoiceProtocol):

    def __init__(self, client: Union[commands.Bot, discord.Client, commands.AutoShardedBot, discord.AutoShardedClient], channel: VoiceChannel):
        super().__init__(client=client, channel=channel)

        self.client: Union[commands.Bot, discord.Client, commands.AutoShardedBot, discord.AutoShardedClient] = client
        self._bot: Union[commands.Bot, discord.Client, commands.AutoShardedBot, discord.AutoShardedClient] = client
        self.channel: VoiceChannel = channel
        self._guild: discord.Guild = channel.guild
        self._dj: discord.Member = None

        self._node: Node = NodePool.get_node()
        self._current: objects.Track = None
        self._filter: filters.Filter = None
        self._volume: int = 100
        self._paused: bool = False
        self._is_connected: bool = False

        self._position: int = 0
        self._last_update: int = 0
        self._current_track_id = None


        self._session_id: Optional[str] = None
        self._voice_server_update_data: Optional[dict] = None


    def __repr__(self):
        return f"<Pomice.player bot={self._bot} guildId={self._guild.id} is_connected={self.is_connected} is_playing={self.is_playing}>"

    @property
    def position(self):

        if not self.is_playing or not self._current:
            return 0

        if self.is_paused:
            return min(self._last_position, self._current.length)

        difference = (time.time() * 1000) - self._last_update
        position = self._last_position + difference

        if position > self.current.length:
            return 0

        return min(position, self.current.length)

    @property
    def is_connected(self):
        return self._is_connected

    @property
    def is_playing(self):
        return self._is_connected and self._current is not None

    @property
    def is_paused(self):
        return self._is_connected and self._paused is True

    @property
    def node(self):
        return self._node

    @property
    def current(self):
        return self._current

    @property
    def volume(self):
        return self._volume


    async def _update_state(self, data: dict):

        state: dict = data.get('state')
        self._last_update = time.time() * 1000
        self._is_connected = state.get('connected')
        self._last_position = state.get('position')

    async def _dispatch_voice_update(self) -> None:

        if not self._session_id or not self._voice_server_update_data:
            return

        await self._node.send(op='voiceUpdate', sessionId=self._session_id, guildId=str(self._guild.id), event={**self._voice_server_update_data})

    async def _voice_server_update(self, data: dict):

        self._voice_server_update_data = data
        await self._dispatch_voice_update()

        
    async def _voice_state_update(self, data: dict):

        if not (channel_id := data.get('channel_id')):
            self.channel, self._session_id, self._voice_server_update_data = None
            return

        self.channel = self._guild.get_channel(int(channel_id))
        self._session_id = data.get('session_id')
        await self._dispatch_voice_update()

    async def _dispatch_event(self, data: dict):
        event_type = data.get('type')
        event = getattr(events, event_type, None)
        event = event(data)
        self._bot.dispatch(f"pomice_{event.name}", event)

    async def get_tracks(self, query: str, ctx: commands.Context = None):
        return await self._node.get_tracks(query, ctx)

    async def connect(self, *, timeout: float, reconnect: bool):
        await self._guild.change_voice_state(channel=self.channel)
        self._node._players[self._guild.id] = self
        self._is_connected = True

        
    async def stop(self):
        self._current = None
        await self._node.send(op='stop', guildId=str(self._guild.id))

    async def disconnect(self, *, force: bool = False):
        await self.stop()
        await self._guild.change_voice_state(channel=None)
        self.cleanup()
        self.channel = None
        self._is_connected = False
        del self._node._players[self._guild.id]


    async def destroy(self):
        await self.disconnect() 
        await self._node.send(op='destroy', guildId=str(self._guild.id))

    async def play(self, track: objects.Track, start_position: int = 0):
        if track.track_id == "spotify":
            track: objects.Track = await self._node.get_tracks(f"{track.title} {track.author}")
        await self._node.send(op='play', guildId=str(self._guild.id), track=track.track_id, startTime=start_position, endTime=track.length, noReplace=False)
        self._current = track
        return self._current

    async def seek(self, position: int):

        if position < 0 or position > self.current.length:
            raise exceptions.TrackInvalidPosition(f"Seek position must be between 0 and the track length")

        await self._node.send(op='seek', guildId=str(self._guild.id), position=position)
        return self.position

    async def set_pause(self, pause: bool):
        await self._node.send(op='pause', guildId=str(self._guild.id), pause=pause)
        self._paused = pause
        return self._paused

    async def set_volume(self, volume: int): 
        await self._node.send(op='volume', guildId=str(self._guild.id), volume=volume)
        self._volume = volume
        return self._volume

    async def set_filter(self, filter: filters.Filter):
        await self._node.send(op='filters', guildId=str(self._guild.id), **filter.payload)
        await self.seek(self.position)
        self._filter = filter
        return filter

  