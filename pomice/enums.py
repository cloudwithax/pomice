from enum import Enum


class SearchType(Enum):
    """The enum for the different search types for Pomice.
       This feature is exclusively for the Spotify search feature of Pomice.
       If you are not using this feature, this class is not necessary.

       SearchType.ytsearch searches using regular Youtube,
       which is best for all scenarios.

       SearchType.ytmsearch searches using YouTube Music,
       which is best for getting audio-only results.

       SearchType.scsearch searches using SoundCloud,
       which is an alternative to YouTube or YouTube Music.
    """
    ytsearch = "ytsearch"
    ytmsearch = "ytmsearch"
    scsearch = "scsearch"

    def __str__(self) -> str:
        return self.value

class NodeAlgorithm(Enum):
    """The enum for the different node algorithms in Pomice.
    
        The enums in this class are to only differentiate different
        methods, since the actual method is handled in the
        get_best_node() method.

        NodeAlgorithm.by_ping returns a node based on it's latency,
        preferring a node with the lowest response time


        NodeAlgorithm.by_players return a nodes based on how many players it has.
        This algorithm prefers nodes with the least amount of players.
    """

    # We don't have to define anything special for these, since these just serve as flags
    by_ping = "BY_PING"
    by_players = "BY_PLAYERS"

    def __str__(self) -> str:
        return self.value

class LoopMode(Enum):
    """The enum for the different loop modes.
       This feature is exclusively for the queue utility of pomice.
       If you are not using this feature, this class is not necessary.

       LoopMode.TRACK sets the queue loop to the current track.

       LoopMode.QUEUE sets the queue loop to the whole queue.

    """
    # We don't have to define anything special for these, since these just serve as flags
    TRACK = "TRACK"
    QUEUE = "queue"
    

    def __str__(self) -> str:
        return self.value