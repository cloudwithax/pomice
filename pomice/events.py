import asyncio

from pomice import exceptions
from .pool import NodePool


class PomiceEvent:
    """The base class for all events dispatched by a node. 
       Every event must be formatted within your bot's code as a listener.
       i.e: If you want to listen for when a track starts, the event would be:
       ```py
       @bot.listen
       async def on_pomice_track_start(self, event):
       ```
    """
    name = "event"
    


class TrackStartEvent(PomiceEvent):
    """Fired when a track has successfully started.
       Returns the player associated with the event and the pomice.Track object.
    """

    def __init__(self, player, track):
        super().__init__()

        self.name = "track_start"
        self.player = player
        self.track = track

    def __repr__(self) -> str:
        return f"<Pomice.TrackStartEvent player={self.player} track_id={self.track.track_id}>"


class TrackEndEvent(PomiceEvent):
    """Fired when a track has successfully ended.
       Returns the player associated with the event along with the pomice.Track object and reason.
    """

    def __init__(self, player, track, reason):
        super().__init__()

        self.name = "track_end"
        self.player = player
        self.track = track
        self.reason = reason

    def __repr__(self) -> str:
        return f"<Pomice.TrackEndEvent player={self.player} track_id={self.track.track_id} reason={self.reason}>"


class TrackStuckEvent(PomiceEvent):
    """Fired when a track is stuck and cannot be played. Returns the player
       associated with the event along with the pomice.Track object to be further parsed by the end user.
    """

    def __init__(self, player, track, threshold):
        super().__init__()

        self.name = "track_stuck"
        self.player = player

        self.track = track
        self.threshold = threshold

    def __repr__(self) -> str:
        return f"<Pomice.TrackStuckEvent player={self.player} track_id={self.track.track_id} threshold={self.threshold}>"


class TrackExceptionEvent(PomiceEvent):
    """Fired when a track error has occured.
       Returns the player associated with the event along with the error code and exception.
    """

    def __init__(self, player, track, error):
        super().__init__()

        self.name = "track_exception"
        self.player = player
        self.track = track
        self.error = error

    def __repr__(self) -> str:
        return f"<Pomice.TrackExceptionEvent player={self.player} error={self.error} exeception={self.exception}>"


class WebSocketClosedEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been closed.
       Returns the reason and the error code.
    """

    def __init__(self, guild, reason, code):
        super().__init__()

        self.name = "websocket_closed"
        self.guild = guild
        self.reason = reason
        self.code = code

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketClosedEvent guild_id={self.guild.id} reason={self.reason} code={self.code}>"


class WebSocketOpenEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been initiated.
       Returns the target and the session SSRC.
    """

    def __init__(self, target, ssrc):
        super().__init__()

        self.name = "websocket_open"

        self.target: str = target
        self.ssrc: int = ssrc

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketOpenEvent target={self.target} ssrc={self.ssrc}>"
