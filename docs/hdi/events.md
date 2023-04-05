# Use the Events class

Pomice has different events that are triggered depending on events that Lavalink emits:
- `Event.TrackEndEvent()`
- `Event.TrackExceptionEvent()`
- `Event.TrackStartEvent()`
- `Event.TrackStuckEvent()`
- `Event.WebsoocketClosedEvent()`
- `Event.WebsocketOpenEvent()`


The classes listed here are as they appear in Pomice. When you use them within your application,
the way you use them will be different. Here's an example on how you would use the `TrackStartEvent` within an event listener in a cog:

```py

@commands.Cog.listener
async def on_pomice_track_start(self, player: Player, track: Track):
    ...

```

## Event definitions

Each event within Pomice has an event definition you can use to listen for said event within
your application. Here are all the definitions:

- `Event.TrackEndEvent()` -> `on_pomice_track_end`
- `Event.TrackExceptionEvent()` -> `on_pomice_track_exception`
- `Event.TrackStartEvent()` -> `on_pomice_track_start`
- `Event.TrackStuckEvent()` -> `on_pomice_track_stuck`
- `Event.WebsocketClosedEvent()` -> `on_pomice_websocket_closed`
- `Event.WebsocketOpenEvent()` -> `on_pomice_websocket_open`


All events related to tracks carry a `Player` object so you can access player-specific functions
and properties for further evaluation. They also carry a `Track` object so you can access track-specific functions and properties for further evaluation as well.

`Event.TrackEndEvent()` carries the reason for the track ending. If the track ends suddenly, you can use the reason provided to determine a solution.

`Event.TrackExceptionEvent()` carries the exception, or reason why the track failed to play. The format for the exception is `REASON: [SEVERITY]`.

`Event.TrackStuckEvent()` carries the threshold, or amount of time Lavalink will wait before it discards the stuck track and stops it from playing.

`Event.WebsocketClosedEvent()` carries a payload object that contains a `Guild` object, the code number, the reason for disconnect and whether or not it was by the
remote, or the node.

`Event.WebsocketOpenEvent()` carries a target, which is usually the node IP, and the SSRC, a 32-bit integer uniquely identifying the source of the RTP packets sent from
Lavalink.
