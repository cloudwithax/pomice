from .pool import NodePool


class PomiceEvent:
    """The base class for all events dispatched by a node. 
        Every event must be formatted within your bots code as a listener.
        i.e: If you want to listen for when a track starts, the event would be:
        ```py
        @bot.listen
        async def on_pomice_track_start(self, event):
        ```
    """
    def __init__(self):
        pass 

    name = 'event'

class TrackStartEvent(PomiceEvent):
    """Fired when a track has successfully started. Returns the player associated with said track and the track ID"""
    def __init__(self, data):
        super().__init__()

        self.name = "track_start"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))
        self.track_id = data['track']

    def __repr__(self) -> str:
        return f"<Pomice.TrackStartEvent track_id={self.track_id}>"

        

class TrackEndEvent(PomiceEvent):
    """Fired when a track has successfully ended. Returns the player associated with the track along with the track ID and reason."""
    def __init__(self, data):
        super().__init__()

        self.name = "track_end"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))
        self.track_id = data['track']
        self.reason = data['reason']

    def __repr__(self) -> str:
        return f"<Pomice.TrackEndEvent track_id={self.track_id} reason={self.reason}>"

class TrackStuckEvent(PomiceEvent):
    """Fired when a track is stuck and cannot be played. Returns the player associated with the track along with a track ID to be further parsed by the end user."""
    def __init__(self, data):
        super().__init__()

        self.name = "track_stuck"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.track_id = data["track"]
        self.threshold = data["thresholdMs"]

    def __repr__(self) -> str:
        return f"<Pomice.TrackStuckEvent track_id={self.track_id} threshold={self.threshold}>"

class TrackExceptionEvent(PomiceEvent):
    """Fired when a track error has occured. Returns the player associated with the track along with the error code and execption"""
    def __init__(self, data):
        super().__init__()

        self.name = "track_exception"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.error = data["error"]
        self.exception = data["exception"]

    def __repr__(self) -> str:
        return f"<Pomice.TrackExceptionEvent> error={self.error} exeception={self.exception}"

class WebsocketClosedEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been closed. Returns the reason and the error code."""
    def __init__(self, data):
        super().__init__()

        self.name = "websocket_closed"

        self.reason = data["reason"]
        self.code = data["code"]

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketClosedEvent reason={self.reason} code={self.code}>"

class WebsocketOpenEvent(PomiceEvent):
    """Fired when a websocket connection to a node has been initiated. Returns the target and the session SSRC."""
    def __init__(self, data):
        super().__init__()

        self.name = "websocket_open"
        
        self.target: str = data['target']
        self.ssrc: int = data['ssrc']

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketOpenEvent target={self.target} ssrc={self.ssrc}>"
