from .track import Track
from typing import List


class Playlist:
    """The base class for a Spotify playlist"""

    def __init__(self, data: dict, tracks: List[Track]) -> None:
        self.name = data["name"]
        self.tracks = tracks
        self.owner = data["owner"]["display_name"]
        self.total_tracks = data["tracks"]["total"]
        self.id = data["id"]
        self.image = data["images"][0]["url"]
        self.uri = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Playlist name={self.name} owner={self.owner} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )
