import re
from typing import List, Optional, Union
from discord import Member, User

from discord.ext import commands

from .enums import SearchType
from .filters import Filter

from . import (
    spotify,
    applemusic
)

SOUNDCLOUD_URL_REGEX = re.compile(
    r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com\/[\w\-\.]+(\/)+[\w\-\.]+/?$"
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
        spotify: bool = False,
        apple_music: bool = False,
        am_track: applemusic.Song = None,
        search_type: SearchType = SearchType.ytsearch,
        spotify_track: spotify.Track = None,
        filters: Optional[List[Filter]] = None,
        timestamp: Optional[float] = None,
        requester: Optional[Union[Member, User]] = None
    ):
        self.track_id = track_id
        self.info = info
        self.spotify = spotify
        self.apple_music = apple_music
        self.filters: List[Filter] = filters
        self.timestamp: Optional[float] = timestamp

        if spotify or apple_music:
            self.original: Optional[Track] = None 
        else:
            self.original = self
        self._search_type = search_type
        self.spotify_track = spotify_track
        self.am_track = am_track

        self.title = info.get("title")
        self.author = info.get("author")
        self.uri = info.get("uri")
        self.identifier = info.get("identifier")
        self.isrc = info.get("isrc")
        
        if self.uri:
            if info.get("thumbnail"):
                self.thumbnail = info.get("thumbnail") 
            elif SOUNDCLOUD_URL_REGEX.match(self.uri):
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
        ctx: Optional[commands.Context] = None,
        spotify: bool = False,
        spotify_playlist: spotify.Playlist = None,
        apple_music: bool = False,
        am_playlist: applemusic.Playlist = None
    ):
        self.playlist_info = playlist_info
        self.tracks_raw = tracks
        self.spotify = spotify
        self.name = playlist_info.get("name")
        self.spotify_playlist = spotify_playlist
        self.apple_music = apple_music
        self.am_playlist = am_playlist

        self._thumbnail = None
        self._uri = None
        
        if self.spotify:
            self.tracks = tracks
            self._thumbnail = self.spotify_playlist.image
            self._uri = self.spotify_playlist.uri
        
        elif self.apple_music:
            self.tracks = tracks
            self._thumbnail = self.am_playlist.image
            self._uri = self.am_playlist.url

        else:
            self.tracks = [
                Track(track_id=track["track"], info=track["info"], ctx=ctx)
                for track in self.tracks_raw
            ]
            self._thumbnail = None
            self._uri = None

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
