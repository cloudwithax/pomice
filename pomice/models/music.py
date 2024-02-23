from __future__ import annotations

from typing import List
from typing import Optional

from discord.ext.commands import Context
from discord.user import _UserTag
from pydantic import Field
from pydantic import model_validator

from pomice.enums import PlaylistType
from pomice.enums import SearchType
from pomice.enums import TrackType
from pomice.filters import Filter
from pomice.models import BaseModel

__all__ = (
    "Track",
    "TrackInfo",
)


class TrackInfo(BaseModel):
    identifier: str
    title: str
    author: str
    length: int
    position: int = 0
    is_stream: bool = Field(default=False, alias="isStream")
    is_seekable: bool = Field(default=False, alias="isSeekable")
    uri: Optional[str] = None
    isrc: Optional[str] = None
    source_name: Optional[str] = Field(default=None, alias="sourceName")
    artwork_url: Optional[str] = Field(default=None, alias="artworkUrl")


class Track(BaseModel):
    """The base track object. Returns critical track information needed for parsing by Lavalink.
    You can also pass in commands.Context to get a discord.py Context object in your track.
    """

    track_id: str = Field(alias="encoded")
    track_type: TrackType
    info: TrackInfo
    search_type: SearchType = SearchType.YTSEARCH
    filters: List[Filter] = Field(default_factory=list)
    timestamp: Optional[float] = None
    original: Optional[Track] = None
    ctx: Optional[Context] = None
    requester: Optional[_UserTag] = None

    @property
    def title(self) -> str:
        return self.info.title

    @property
    def author(self) -> str:
        return self.info.author

    @property
    def uri(self) -> Optional[str]:
        return self.info.uri

    @property
    def identifier(self) -> str:
        return self.info.identifier

    @property
    def isrc(self) -> Optional[str]:
        return self.info.isrc

    @property
    def thumbnail(self) -> Optional[str]:
        return self.info.artwork_url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Track):
            return False

        return self.track_id == other.track_id

    def __str__(self) -> str:
        return self.info.title

    def __repr__(self) -> str:
        return f"<Pomice.Track title={self.info.title!r} uri=<{self.info.uri!r}> length={self.info.length}>"

    @model_validator(mode="after")
    def _set_thumbnail_url(self) -> Track:
        if self.track_type is TrackType.YOUTUBE and not self.info.artwork_url:
            self.info.artwork_url = (
                f"https://img.youtube.com/vi/{self.info.identifier}/mqdefault.jpg"
            )
        return self


class PlaylistInfo(BaseModel):
    name: str
    selected_track: int = Field(default=0, alias="selectedTrack")


class Playlist(BaseModel):
    """The base playlist object.
    Returns critical playlist information needed for parsing by Lavalink.
    """

    info: PlaylistInfo
    tracks: List[Track]
    playlist_type: PlaylistType
    uri: str
    artwork_url: Optional[str] = None

    @property
    def name(self) -> str:
        return self.info.name

    @property
    def thumbnail(self) -> Optional[str]:
        return self.artwork_url

    @property
    def selected_track(self) -> Optional[Track]:
        if self.track_count <= 0:
            return None

        return self.tracks[self.info.selected_track]

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    def __str__(self) -> str:
        return self.info.name

    def __repr__(self) -> str:
        return f"<Pomice.Playlist name={self.info.name!r} total_tracks={self.track_count}>"
