from typing import Dict
from typing import List
from typing import Optional

from discord.ext.commands import Context
from discord.user import _UserTag
from pydantic import Field

from pomice.enums import SearchType
from pomice.enums import TrackType
from pomice.filters import Filter
from pomice.models import BaseModel
from pomice.models.music import Track
from pomice.models.music import TrackInfo


class SpotifyTrackRaw(BaseModel):
    id: str
    name: str
    artists: List[Dict[str, str]]
    duration_ms: float
    external_ids: Dict[str, str] = Field(default_factory=dict)
    external_urls: Dict[str, str] = Field(default_factory=dict)
    album: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)

    def build_track(
        self,
        image: Optional[str] = None,
        filters: Optional[List[Filter]] = None,
        ctx: Optional[Context] = None,
        requester: Optional[_UserTag] = None,
    ) -> Track:
        if self.album:
            image = self.album["images"][0]["url"]

        return Track(
            track_id=self.id,
            track_type=TrackType.SPOTIFY,
            search_type=SearchType.YTMSEARCH,
            filters=filters,
            ctx=ctx,
            requester=requester,
            info=TrackInfo(
                identifier=self.id,
                title=self.name,
                author=", ".join(artist["name"] for artist in self.artists),
                length=self.duration_ms,
                is_seekable=True,
                uri=self.external_urls.get("spotify", ""),
                artwork_url=image,
                isrc=self.external_ids.get("isrc"),
            ),
        )
