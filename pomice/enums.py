from enum import Enum

class SearchType(Enum):
    """The base class for the different search types for Pomice. 
    This feature is exclusively for the Spotify search feature of Pomice.
    If you are not using this feature, this class is not necessary.

    SearchType.YTSEARCH searches for a Spotify track using regular Youtube, which is best for all scenarios

    SearchType.YTMSEARCH searches for a Spotify track using YouTube Music, which is best for getting audio-only results.

    SearchType.SCSEARCH searches for a Spotify track using SoundCloud, which is an alternative to YouTube or YouTube Music.
    """
    YTSEARCH = 'ytsearch:'
    YTMSEARCH = 'ytmsearch:'
    SCSEARCH = 'scsearch:'
    
    def __str__(self) -> str:
        return self.value




    
        
    