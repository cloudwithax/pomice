from discord.ext import commands

class Track:

    def __init__(self, track_id: str, info: dict, ctx: commands.Context = None):

        self.track_id = track_id
        self.info = info

        self.title = info.get("title")
        self.author = info.get("author")
        self.length = info.get("length")
        if ctx:
            self.ctx: commands.Context = ctx
            self.requester = self.ctx.author
        self.identifier = info.get("identifier")
        self.uri = info.get("uri")
        self.is_stream = info.get("isStream")
        self.is_seekable = info.get("isSeekable")
        self.position = info.get("position")

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"<Pomice.track title={self.title!r} uri=<{self.uri!r}> length={self.length}>"


class Playlist:

    def __init__(self, playlist_info: dict, tracks: list, ctx: commands.Context = None):

        self.playlist_info = playlist_info
        self.tracks_raw = tracks

        self.name = playlist_info.get("name")
        self.selected_track = playlist_info.get("selectedTrack")

        self.tracks = [Track(track_id=track["track"], info=track["info"], ctx=ctx) for track in self.tracks_raw]
        

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Pomice.playlist name={self.name!r} track_count={len(self.tracks)}>"