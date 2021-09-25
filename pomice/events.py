from .pool import NodePool


class PomiceEvent:
    def __init__(self):
        pass 

    name = 'event'

class TrackStartEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "track_start"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))
        self.track_id = data['track']

    def __repr__(self) -> str:
        return f"<Pomice.TrackStartEvent track_id={self.track_id}>"

        

class TrackEndEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "track_end"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))
        self.track_id = data['track']
        self.reason = data['reason']

    def __repr__(self) -> str:
        return f"<Pomice.TrackEndEvent track_id={self.track_id} reason={self.reason}>"

class TrackStuckEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "track_stuck"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.track_id = data["track"]
        self.threshold = data["thresholdMs"]

    def __repr__(self) -> str:
        return f"<Pomice.TrackStuckEvent track_id={self.track_id} threshold={self.threshold}>"

class TrackExceptionEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "track_exception"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.error = data["error"]
        self.exception = data["exception"]

    def __repr__(self) -> str:
        return f"<Pomice.TrackExceptionEvent> error={self.error} exeception={self.exception}"

class WebsocketClosedEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "websocket_closed"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.reason = data["reason"]
        self.code = data["code"]

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketClosedEvent reason={self.reason} code={self.code}>"

class WebsocketOpenEvent(PomiceEvent):
    def __init__(self, data):
        super().__init__()

        self.name = "websocket_open"
        self.player = NodePool.get_node().get_player(int(data["guildId"]))

        self.target: str = data['target']
        self.ssrc: int = data['ssrc']

    def __repr__(self) -> str:
        return f"<Pomice.WebsocketOpenEvent target={self.target} ssrc={self.ssrc}>"
