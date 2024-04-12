from __future__ import annotations

import abc
from enum import Enum
from enum import unique
from typing import Literal
from typing import TYPE_CHECKING

from discord import Guild
from pydantic import computed_field
from pydantic import Field

from pomice.models import BaseModel
from pomice.objects import Track
from pomice.player import Player
from pomice.pool import NodePool

if TYPE_CHECKING:
    from discord import Client

__all__ = (
    "PomiceEvent",
    "TrackStartEvent",
    "TrackEndEvent",
    "TrackStuckEvent",
    "TrackExceptionEvent",
    "WebSocketClosedPayload",
    "WebSocketClosedEvent",
    "WebSocketOpenEvent",
)


class PomiceEvent(BaseModel, abc.ABC):
    """The base class for all events dispatched by a node.
    Every event must be formatted within your bot's code as a listener.
    i.e: If you want to listen for when a track starts, the event would be:
    ```py
    @bot.listen
    async def on_pomice_track_start(self, event):
    ```
    """

    name: str

    @abc.abstractmethod
    def dispatch(self, bot: Client) -> None:
        ...


class TrackStartEvent(PomiceEvent):
    """Fired when a track has successfully started.
    Returns the player associated with the event and the pomice.Track object.
    """

    name: Literal["track_start"]
    player: Player
    track: Track

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.player, self.track)

    def __repr__(self) -> str:
        return f"<Pomice.TrackStartEvent player={self.player!r} track={self.track!r}>"


@unique
class TrackEndEventReason(str, Enum):
    FINISHED = "finished"
    LOAD_FAILED = "loadfailed"
    STOPPED = "stopped"
    REPLACED = "replaced"
    CLEANUP = "cleanup"

    @classmethod
    def _missing_(cls, value: object) -> TrackEndEventReason:
        if isinstance(value, str):
            return TrackEndEventReason(value.casefold())


class TrackEndEvent(PomiceEvent):
    """Fired when a track has successfully ended.
    Returns the player associated with the event along with the pomice.Track object and reason.
    """

    name: Literal["track_end"]
    player: Player
    track: Track
    reason: TrackEndEventReason

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.player, self.track, self.reason)

    def __repr__(self) -> str:
        return f"<Pomice.TrackEndEvent player={self.player!r} track={self.track!r} reason={self.reason!r}>"


class TrackStuckEvent(PomiceEvent):
    """Fired when a track has been stuck for a while.
    Returns the player associated with the event along with the pomice.Track object and threshold.
    """

    name: Literal["track_stuck"]
    player: Player
    track: Track
    threshold: float = Field(alias="thresholdMs")

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.player, self.track, self.threshold)

    def __repr__(self) -> str:
        return f"<Pomice.TrackStuckEvent player={self.player!r} track={self.track!r} threshold={self.threshold!r}>"


class TrackExceptionEvent(PomiceEvent):
    """Fired when there is an exception while playing a track.
    Returns the player associated with the event along with the pomice.Track object and exception.
    """

    name: Literal["track_exception"]
    player: Player
    track: Track
    exception: str = Field(alias="error")

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.player, self.track, self.exception)

    def __repr__(self) -> str:
        return f"<Pomice.TrackExceptionEvent player={self.player!r} track={self.track!r} exception={self.exception!r}>"


class WebSocketClosedPayload(BaseModel):
    """The payload for the WebSocketClosedEvent."""

    guild_id: int = Field(alias="guildId")
    code: int
    reason: str
    by_remote: bool = Field(alias="byRemote")

    @computed_field
    @property
    def guild(self) -> Guild:
        return NodePool.get_node().bot.get_guild(self.guild_id)

    def __repr__(self) -> str:
        return (
            f"<Pomice.WebSocketClosedPayload guild_id={self.guild_id!r} code={self.code!r} "
            f"reason={self.reason!r} by_remote={self.by_remote!r}>"
        )


class WebSocketClosedEvent(PomiceEvent):
    """Fired when the websocket connection to the node is closed.
    Returns the player associated with the event and the code and reason for the closure.
    """

    name: Literal["websocket_closed"]
    payload: WebSocketClosedPayload

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.payload)

    def __repr__(self) -> str:
        return f"<Pomice.WebSocketClosedEvent payload={self.payload!r}>"


class WebSocketOpenEvent(PomiceEvent):
    """Fired when the websocket connection to the node is opened.
    Returns the player associated with the event.
    """

    name: Literal["websocket_open"]
    target: str
    ssrc: str

    def dispatch(self, bot: Client) -> None:
        bot.dispatch(f"pomice_{self.name}", self.target, self.ssrc)

    def __repr__(self) -> str:
        return f"<Pomice.WebSocketOpenEvent target={self.target!r} ssrc={self.ssrc!r}>"
