import re
from enum import Enum
from enum import IntEnum
from enum import unique

__all__ = (
    "SearchType",
    "TrackType",
    "PlaylistType",
    "NodeAlgorithm",
    "LoopMode",
    "RouteStrategy",
    "RouteIPType",
    "URLRegex",
    "LogLevel",
)


class BaseStrEnum(str, Enum):
    def __str__(self):
        return self.value


@unique
class SearchType(BaseStrEnum):
    """
    The enum for the different search types for Pomice.
    This feature is exclusively for the Spotify search feature of Pomice.
    If you are not using this feature, this class is not necessary.

    SearchType.ytsearch searches using regular Youtube,
    which is best for all scenarios.

    SearchType.ytmsearch searches using YouTube Music,
    which is best for getting audio-only results.

    SearchType.scsearch searches using SoundCloud,
    which is an alternative to YouTube or YouTube Music.
    """

    YTSEARCH = "ytsearch"
    YTMSEARCH = "ytmsearch"
    SCSEARCH = "scsearch"


@unique
class TrackType(BaseStrEnum):
    """
    The enum for the different track types for Pomice.

    TrackType.YOUTUBE defines that the track is from YouTube

    TrackType.SOUNDCLOUD defines that the track is from SoundCloud.

    TrackType.SPOTIFY defines that the track is from Spotify

    TrackType.APPLE_MUSIC defines that the track is from Apple Music.

    TrackType.HTTP defines that the track is from an HTTP source.

    TrackType.LOCAL defines that the track is from a local source.
    """

    # We don't have to define anything special for these, since these just serve as flags
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    HTTP = "http"
    LOCAL = "local"


@unique
class PlaylistType(BaseStrEnum):
    """
    The enum for the different playlist types for Pomice.

    PlaylistType.YOUTUBE defines that the playlist is from YouTube

    PlaylistType.SOUNDCLOUD defines that the playlist is from SoundCloud.

    PlaylistType.SPOTIFY defines that the playlist is from Spotify

    PlaylistType.APPLE_MUSIC defines that the playlist is from Apple Music.
    """

    # We don't have to define anything special for these, since these just serve as flags
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"


@unique
class NodeAlgorithm(BaseStrEnum):
    """
    The enum for the different node algorithms in Pomice.

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


@unique
class LoopMode(BaseStrEnum):
    """
    The enum for the different loop modes.
    This feature is exclusively for the queue utility of pomice.
    If you are not using this feature, this class is not necessary.

    LoopMode.TRACK sets the queue loop to the current track.

    LoopMode.QUEUE sets the queue loop to the whole queue.
    """

    # We don't have to define anything special for these, since these just serve as flags
    TRACK = "track"
    QUEUE = "queue"


@unique
class RouteStrategy(BaseStrEnum):
    """
    The enum for specifying the route planner strategy for Lavalink.
    This feature is exclusively for the RoutePlanner class.
    If you are not using this feature, this class is not necessary.

    RouteStrategy.ROTATE_ON_BAN specifies that the node is rotating IPs
    whenever they get banned by Youtube.

    RouteStrategy.LOAD_BALANCE specifies that the node is selecting
    random IPs to balance out requests between them.

    RouteStrategy.NANO_SWITCH specifies that the node is switching
    between IPs every CPU clock cycle.

    RouteStrategy.ROTATING_NANO_SWITCH specifies that the node is switching
    between IPs every CPU clock cycle and is rotating between IP blocks on
    ban.
    """

    ROTATE_ON_BAN = "RotatingIpRoutePlanner"
    LOAD_BALANCE = "BalancingIpRoutePlanner"
    NANO_SWITCH = "NanoIpRoutePlanner"
    ROTATING_NANO_SWITCH = "RotatingNanoIpRoutePlanner"


@unique
class RouteIPType(BaseStrEnum):
    """
    The enum for specifying the route planner IP block type for Lavalink.
    This feature is exclusively for the RoutePlanner class.
    If you are not using this feature, this class is not necessary.

    RouteIPType.IPV4 specifies that the IP block type is IPV4

    RouteIPType.IPV6 specifies that the IP block type is IPV6
    """

    IPV4 = "Inet4Address"
    IPV6 = "Inet6Address"


@unique
class LogLevel(IntEnum):
    """
    The enum for specifying the logging level within Pomice.
    This class serves as shorthand for logging.<level>
    This enum is exclusively for the logging feature in Pomice.
    If you are not using this feature, this class is not necessary.


    LogLevel.DEBUG sets the logging level to "debug".

    LogLevel.INFO sets the logging level to "info".

    LogLevel.WARN sets the logging level to "warn".

    LogLevel.ERROR sets the logging level to "error".

    LogLevel.CRITICAL sets the logging level to "CRITICAL".
    """

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_str(cls, level_str):
        try:
            return cls[level_str.upper()]
        except KeyError:
            raise ValueError(f"No such log level: {level_str}")


class URLRegex:
    """
    The class for all the URL Regexes in use by Pomice.

    URLRegex.SPOTIFY_URL returns the Spotify URL Regex.

    URLRegex.DISCORD_MP3_URL returns the Discord MP3 URL Regex.

    URLRegex.YOUTUBE_URL returns the Youtube URL Regex.

    URLRegex.YOUTUBE_PLAYLIST returns the Youtube Playlist Regex.

    URLRegex.YOUTUBE_TIMESTAMP returns the Youtube Timestamp Regex.

    URLRegex.AM_URL returns the Apple Music URL Regex.

    URLRegex.SOUNDCLOUD_URL returns the SoundCloud URL Regex.

    URLRegex.BASE_URL returns the standard URL Regex.
    """

    SPOTIFY_URL = re.compile(
        r"https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)",
    )

    DISCORD_MP3_URL = re.compile(
        r"https?://cdn.discordapp.com/attachments/(?P<channel_id>[0-9]+)/"
        r"(?P<message_id>[0-9]+)/(?P<file>[a-zA-Z0-9_.]+)+",
    )

    YOUTUBE_URL = re.compile(
        r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))"
        r"(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$",
    )

    YOUTUBE_PLAYLIST_URL = re.compile(
        r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))/playlist\?list=.*",
    )

    YOUTUBE_TIMESTAMP = re.compile(
        r"(?P<video>^.*?)(\?t|&start)=(?P<time>\d+)?.*",
    )

    AM_URL = re.compile(
        r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/"
        r"(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^?]+)",
    )

    AM_SINGLE_IN_ALBUM_REGEX = re.compile(
        r"https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/"
        r"(?P<name>.+)/(?P<id>.+)(\?i=)(?P<id2>.+)",
    )

    SOUNDCLOUD_URL = re.compile(
        r"((?:https?:)?\/\/)?((?:www|m)\.)?soundcloud.com\/.*/.*",
    )

    SOUNDCLOUD_PLAYLIST_URL = re.compile(
        r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com\/.*/sets/.*",
    )

    SOUNDCLOUD_TRACK_IN_SET_URL = re.compile(
        r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com/[a-zA-Z0-9-._]+/[a-zA-Z0-9-._]+(\?in)",
    )

    LAVALINK_SEARCH = re.compile(r"(?P<type>ytm?|sc)search:")

    BASE_URL = re.compile(r"https?://(?:www\.)?.+")
