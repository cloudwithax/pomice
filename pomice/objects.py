from __future__ import annotations

from typing import List
from typing import Optional

from .enums import PlaylistType
from .enums import SearchType
from .enums import TrackType
from .filters import Filter

__all__ = (
    "Track",
    "Playlist",
)


class Track:
    """The base track object. Returns critical track information needed for parsing by Lavalink.
    You can also pass in commands.Context to get a discord.py Context object in your track.
    """

    __slots__ = (
        "track_id",
        "info",
        "track_type",
        "filters",
        "timestamp",
        "original",
        "_search_type",
        "playlist",
        "title",
        "author",
        "uri",
        "identifier",
        "isrc",
        "thumbnail",
        "length",
        "ctx",
        "requester",
        "is_stream",
        "is_seekable",
        "position",
    )

    def __init__(
        self,
        *,
        track_id: str,
        info: dict,
        track_type: TrackType,
        search_type: SearchType = SearchType.ytsearch,
        filters: Optional[List[Filter]] = None,
        timestamp: Optional[float] = None,
    ):
        self.track_id: str = track_id
        self.info: dict = info
        self.track_type: TrackType = track_type
        self.filters: Optional[List[Filter]] = filters
        self.timestamp: Optional[float] = timestamp

        if self.track_type == TrackType.SPOTIFY or self.track_type == TrackType.APPLE_MUSIC:
            self.original: Optional[Track] = None
        else:
            self.original = self
        self._search_type: SearchType = search_type

        self.playlist: Optional[Playlist] = None

        self.title: str = info.get("title", "Unknown Title")
        self.author: str = info.get("author", "Unknown Author")
        self.uri: str = info.get("uri", "")
        self.identifier: str = info.get("identifier", "")
        self.isrc: Optional[str] = info.get("isrc", None)
        self.thumbnail: Optional[str] = info.get("thumbnail")

        if self.uri and self.track_type is TrackType.YOUTUBE:
            self.thumbnail = f"https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg"

        self.length: int = info.get("length", 0)
        self.is_stream: bool = info.get("isStream", False)
        self.is_seekable: bool = info.get("isSeekable", False)
        self.position: int = info.get("position", 0)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Track):
            return False

        return other.track_id == self.track_id

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f"<Pomice.track title={self.title!r} uri=<{self.uri!r}> length={self.length}>"


class Playlist:
    """The base playlist object.
    Returns critical playlist information needed for parsing by Lavalink.
    You can also pass in commands.Context to get a discord.py Context object in your tracks.
    """

    __slots__ = (
        "playlist_info",
        "tracks",
        "name",
        "playlist_type",
        "_thumbnail",
        "_uri",
        "selected_track",
        "track_count",
    )

    def __init__(
        self,
        *,
        playlist_info: dict,
        tracks: list,
        playlist_type: PlaylistType,
        thumbnail: Optional[str] = None,
        uri: Optional[str] = None,
    ):
        self.playlist_info: dict = playlist_info
        self.tracks: List[Track] = tracks
        self.name: str = playlist_info.get("name", "Unknown Playlist")
        self.playlist_type: PlaylistType = playlist_type

        self._thumbnail: Optional[str] = thumbnail
        self._uri: Optional[str] = uri

        for track in self.tracks:
            track.playlist = self

        self.selected_track: Optional[Track] = None
        if (index := playlist_info.get("selectedTrack", -1)) != -1:
            self.selected_track = self.tracks[index]

        self.track_count: int = len(self.tracks)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Pomice.playlist name={self.name!r} track_count={len(self.tracks)}>"

    @property
    def uri(self) -> Optional[str]:
        """Returns either an Apple Music/Spotify URL/URI, or None if its neither of those."""
        return self._uri

    @property
    def thumbnail(self) -> Optional[str]:
        """Returns either an Apple Music/Spotify album/playlist thumbnail, or None if its neither of those."""
        return self._thumbnail
