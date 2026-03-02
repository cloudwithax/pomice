__all__ = (
    "PomiceException",
    "NodeException",
    "NodeCreationError",
    "NodeConnectionFailure",
    "NodeConnectionClosed",
    "NodeRestException",
    "NodeNotAvailable",
    "NoNodesAvailable",
    "TrackInvalidPosition",
    "TrackLoadError",
    "FilterInvalidArgument",
    "FilterTagInvalid",
    "FilterTagAlreadyInUse",
    "InvalidSpotifyClientAuthorization",
    "AppleMusicNotEnabled",
    "QueueException",
    "QueueFull",
    "QueueEmpty",
    "LavalinkVersionIncompatible",
)


class PomiceException(Exception):
    """Base of all Pomice exceptions."""


class NodeException(Exception):
    """Base exception for nodes."""


class NodeCreationError(NodeException):
    """There was a problem while creating the node."""


class NodeConnectionFailure(NodeException):
    """There was a problem while connecting to the node."""


class NodeConnectionClosed(NodeException):
    """The node's connection is closed."""

    pass


class NodeRestException(NodeException):
    """A request made using the node's REST uri failed"""

    pass


class NodeNotAvailable(PomiceException):
    """The node is currently unavailable."""

    pass


class NoNodesAvailable(PomiceException):
    """There are no nodes currently available."""

    pass


class TrackInvalidPosition(PomiceException):
    """An invalid position was chosen for a track."""

    pass


class TrackLoadError(PomiceException):
    """There was an error while loading a track."""

    def __init__(self, message: str = "Sorry, I ran into trouble trying to load that track."):
        super().__init__(message)


class FilterInvalidArgument(PomiceException):
    """An invalid argument was passed to a filter."""

    pass


class FilterTagInvalid(PomiceException):
    """An invalid tag was passed or Pomice was unable to find a filter tag"""

    pass


class FilterTagAlreadyInUse(PomiceException):
    """A filter with a tag is already in use by another filter"""

    pass


class InvalidSpotifyClientAuthorization(PomiceException):
    """No Spotify client authorization was provided for track searching."""

    pass


class AppleMusicNotEnabled(PomiceException):
    """An Apple Music Link was passed in when Apple Music functionality was not enabled."""

    pass


class QueueException(Exception):
    """Base Pomice queue exception."""

    pass


class QueueFull(QueueException):
    """Exception raised when attempting to add to a full Queue."""

    def __init__(self, message: str = "Whoops! The queue is completely full right now."):
        super().__init__(message)


class QueueEmpty(QueueException):
    """Exception raised when attempting to retrieve from an empty Queue."""

    def __init__(
        self, message: str = "It looks like the queue is empty. There's no more music to play!",
    ):
        super().__init__(message)


class LavalinkVersionIncompatible(PomiceException):
    """Lavalink version is incompatible. Must be using Lavalink > 3.7.0 to avoid this error."""

    pass
