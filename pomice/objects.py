from re import S
from typing import Optional

from . import SearchType
from discord.ext import commands


class Track:
    """The base track object. Returns critical track information needed for parsing by Lavalink.
       You can also pass in commands.Context to get a discord.py Context object in your track.
    """

    def __init__(
        self,
        track_id: str,
        info: dict,
        ctx: Optional[commands.Context],
        search_type: SearchType = None,
        spotify: bool = False
    ):
        self.track_id = track_id
        self.info = info
        self.spotify = spotify

        self.title = info.get("title")
        self.author = info.get("author")
        self.length = info.get("length")
        self.ctx = ctx
        self.requester = self.ctx.author if ctx else None
        self.identifier = info.get("identifier")
        self.uri = info.get("uri")
        self.is_stream = info.get("isStream")
        self.is_seekable = info.get("isSeekable")
        self.position = info.get("position")

        if self.spotify:
            self.youtube_result = None
            if search_type:
                self.search_type = search_type

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
        playlist_info: dict,
        tracks: list,
        ctx: Optional[commands.Context] = None,
        spotify: bool = False,
        thumbnail: Optional[str] = None,
        uri: Optional[str] = None,
    ):
        self.playlist_info = playlist_info
        self.tracks_raw = tracks
        self.spotify = spotify

        self.name = playlist_info.get("name")
        self.selected_track = playlist_info.get("selectedTrack")

        
        self._thumbnail = thumbnail
        self._uri = uri
        
        if self.spotify:
            self.tracks = tracks

        else:
            self.tracks = [
                Track(track_id=track["track"], info=track["info"], ctx=ctx)
                for track in self.tracks_raw
            ]

        self.track_count = len(self.tracks)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Pomice.playlist name={self.name!r} track_count={len(self.tracks)}>"

    @property
    def uri(self) -> Optional[str]:
        """Spotify album/playlist URI, or None if not a Spotify object."""
        return self._uri

    @property
    def thumbnail(self) -> Optional[str]:
        """Spotify album/playlist thumbnail, or None if not a Spotify object."""
        return self._thumbnail
