from typing import List
from typing import Optional

__all__ = (
    "Track",
    "Playlist",
    "Album",
    "Artist",
)


class Track:
    """The base class for a Spotify Track"""

    def __init__(self, data: dict, image: Optional[str] = None) -> None:
        self.name: str = data["name"]
        self.artists: str = ", ".join(artist["name"] for artist in data["artists"])
        self.length: float = data["duration_ms"]
        self.id: str = data["id"]

        self.isrc: Optional[str] = None
        if data.get("external_ids"):
            self.isrc = data["external_ids"]["isrc"]

        self.image: Optional[str] = image
        if data.get("album") and data["album"].get("images"):
            self.image = data["album"]["images"][0]["url"]

        self.uri: Optional[str] = None
        if not data["is_local"]:
            self.uri = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Track name={self.name} artists={self.artists} "
            f"length={self.length} id={self.id} isrc={self.isrc}>"
        )


class Playlist:
    """The base class for a Spotify playlist"""

    def __init__(self, data: dict, tracks: List[Track]) -> None:
        self.name: str = data["name"]
        self.tracks = tracks
        self.owner: str = data["owner"]["display_name"]
        self.total_tracks: int = data["tracks"]["total"]
        self.id: str = data["id"]
        if data.get("images") and len(data["images"]):
            self.image = data["images"][0]["url"]
        else:
            self.image = self.tracks[0].image
        self.uri = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Playlist name={self.name} owner={self.owner} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )


class Album:
    """The base class for a Spotify album"""

    def __init__(self, data: dict) -> None:
        self.name: str = data["name"]
        self.artists: str = ", ".join(artist["name"] for artist in data["artists"])
        self.image: str = data["images"][0]["url"]
        self.tracks = [Track(track, image=self.image) for track in data["tracks"]["items"]]
        self.total_tracks: int = data["total_tracks"]
        self.id: str = data["id"]
        self.uri: str = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Album name={self.name} artists={self.artists} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )


class Artist:
    """The base class for a Spotify artist"""

    def __init__(self, data: dict, tracks: dict) -> None:
        self.name: str = (
            # Setting that because its only playing top tracks
            f"Top tracks for {data['name']}"
        )
        self.genres: str = ", ".join(genre for genre in data["genres"])
        self.followers: int = data["followers"]["total"]
        self.image: str = data["images"][0]["url"]
        self.tracks = [Track(track, image=self.image) for track in tracks]
        self.id: str = data["id"]
        self.uri: str = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return f"<Pomice.spotify.Artist name={self.name} id={self.id} " f"tracks={self.tracks}>"
