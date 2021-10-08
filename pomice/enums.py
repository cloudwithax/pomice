from enum import Enum
from typing import Literal


class SearchType(Enum):
    """The enum for the different search types for Pomice.
    This feature is exclusively for the Spotify search feature of Pomice.
    If you are not using this feature, this class is not necessary.

    SearchType.ytsearch searches using regular Youtube, which is best for all scenarios.

    SearchType.ytmsearch searches using YouTube Music, which is best for getting audio-only results.

    SearchType.scsearch searches using SoundCloud, which is an alternative to YouTube or YouTube Music.
    """
    ytsearch = "ytsearch"
    ytmsearch = "ytmsearch"
    scsearch = "scsearch"

    def __str__(self) -> str:
        return self.value
