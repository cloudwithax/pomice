class Artist:
    """The base class for a Spotify artist"""

    def __init__(self, data: dict, tracks: dict) -> None:
        self.name = f"Top tracks for {data['name']}" 
        self.genres = ", ".join(genre for genre in data["genres"])
        self.followers = data["followers"]["total"]
        self.image = data["images"][0]["url"]
        self.tracks = tracks
        self.total_tracks = len(tracks)
        self.id = data["id"]
        self.uri = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Artist name={self.name} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )
