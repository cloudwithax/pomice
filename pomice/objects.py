from __future__ import annotations
from typing import List, Optional, Union
from discord import Member, User

from discord.ext import commands

from .enums import SearchType, TrackType, PlaylistType
from .filters import Filter

from . import (
    spotify,
    applemusic
)


class Track:
    """The base track object. Returns critical track information needed for parsing by Lavalink.
       You can also pass in commands.Context to get a discord.py Context object in your track.
    """

    def __init__(
        self,
        *,
        track_id: str,
        info: dict,
        ctx: Optional[commands.Context] = None,
        track_type: TrackType,
        search_type: SearchType = SearchType.ytsearch,
        filters: Optional[List[Filter]] = None,
        timestamp: Optional[float] = None,
        requester: Optional[Union[Member, User]] = None,
    ):
        self.track_id = track_id
        self.info = info
        self.track_type: TrackType = track_type
        self.filters: Optional[List[Filter]] = filters
        self.timestamp: Optional[float] = timestamp

        if self.track_type == TrackType.SPOTIFY or self.track_type == TrackType.APPLE_MUSIC:
            self.original: Optional[Track] = None 
        else:
            self.original = self
        self._search_type = search_type

        self.playlist: Playlist = None

        self.title = info.get("title")
        self.author = info.get("author")
        self.uri = info.get("uri")
        self.identifier = info.get("identifier")
        self.isrc = info.get("isrc")
        
        if self.uri:
            if info.get("thumbnail"):
                self.thumbnail = info.get("thumbnail") 
            elif self.track_type == TrackType.SOUNDCLOUD:
                # ok so theres no feasible way of getting a Soundcloud image URL
                # so we're just gonna leave it blank for brevity
                self.thumbnail = None
            else:
                self.thumbnail = f"https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg"

        self.length = info.get("length")
        self.ctx = ctx
        if requester:
            self.requester = requester
        else:
            self.requester = self.ctx.author if ctx else None
        self.is_stream = info.get("isStream")
        self.is_seekable = info.get("isSeekable")
        self.position = info.get("position")

    def __eq__(self, other):
        if not isinstance(other, Track):
            return False

        if self.ctx and other.ctx:
            return other.track_id == self.track_id and other.ctx.message.id == self.ctx.message.id

        return other.track_id == self.track_id

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Pomice.track title={self.title!r} uri=<{self.uri!r}> length={self.length}>"


class Playlist:
    """The base playlist object.
       Returns critical playlist information needed for parsing by Lavalink.
       You can also pass in commands.Context to get a discord.py Context object in your tracks.
    """

    def __init__(
        self,
        *,
        playlist_info: dict,
        tracks: list,
        playlist_type: PlaylistType,
        thumbnail: Optional[str] = None,
        uri: Optional[str] = None
    ):
        self.playlist_info = playlist_info
        self.tracks: List[Track] = tracks
        self.name = playlist_info.get("name")
        self.playlist_type = playlist_type

        self._thumbnail = thumbnail
        self._uri = uri

        for track in self.tracks:
            track.playlist = self

        if (index := playlist_info.get("selectedTrack")) == -1:
            self.selected_track = None
        else:
            self.selected_track = self.tracks[index]

        self.track_count = len(self.tracks)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Pomice.playlist name={self.name!r} track_count={len(self.tracks)}>"

    @property
    def uri(self) -> Optional[str]:
        """Returns either an Apple Music/Spotify URL/URI, or None if its neither of those."""
        return self._uri

    @property
    def thumbnail(self) -> Optional[str]:
        """Returns either an Apple Music/Spotify album/playlist thumbnail, or None if its neither of those."""
        return self._thumbnail
