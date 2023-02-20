"""Module for managing Apple Music objects"""

from typing import List


class Song:
    """The base class for an Apple Music song"""
    def __init__(self, data: dict) -> None:
       
        self.name: str = data["attributes"]["name"]
        self.url: str = data["attributes"]["url"]
        self.isrc: str = data["attributes"]["isrc"]
        self.length: float = data["attributes"]["durationInMillis"]
        self.id: str = data["id"]
        self.artists: str = data["attributes"]["artistName"]
        self.image: str = data["attributes"]["artwork"]["url"].replace(
            "{w}x{h}", 
            f'{data["attributes"]["artwork"]["width"]}x{data["attributes"]["artwork"]["height"]}'
        )

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Song name={self.name} artists={self.artists} "
            f"length={self.length} id={self.id} isrc={self.isrc}>"
        )
   

class Playlist:
    """The base class for an Apple Music playlist"""
    def __init__(self, data: dict, tracks: List[Song]) -> None:
        self.name: str = data["attributes"]["name"]
        self.owner: str = data["attributes"]["curatorName"]
        self.id: str = data["id"]
        self.tracks: List[Song] = tracks
        self.total_tracks: int = len(tracks)
        self.url: str = data["attributes"]["url"]
        # we'll use the first song's image as the image for the playlist
        # because apple dynamically generates playlist covers client-side
        self.image = self.tracks[0].image 
        print("worked")

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Playlist name={self.name} owner={self.owner} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )

             
class Album:
    """The base class for an Apple Music album"""
    def __init__(self, data: dict) -> None:
        self.name: str = data["attributes"]["name"]
        self.url: str = data["attributes"]["url"]
        self.id: str = data["id"]
        self.artists: str = data["attributes"]["artistName"]
        self.total_tracks: int = data["attributes"]["trackCount"]
        self.tracks: List[Song] = [Song(track) for track in data["relationships"]["tracks"]["data"]]
        self.image: str = data["attributes"]["artwork"]["url"].replace(
            "{w}x{h}", 
            f'{data["attributes"]["artwork"]["width"]}x{data["attributes"]["artwork"]["height"]}'
        )

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Album name={self.name} artists={self.artists} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )
        


class Artist:
    """The base class for an Apple Music artist"""
    def __init__(self, data: dict, tracks: dict) -> None:
        self.name: str = f'Top tracks for {data["attributes"]["name"]}'
        self.url: str = data["attributes"]["url"]
        self.id: str = data["id"]
        self.genres: str = ", ".join(genre for genre in data["attributes"]["genreNames"])
        self.tracks: List[Song] = [Song(track) for track in tracks]
        self.image: str = data["attributes"]["artwork"]["url"].replace(
            "{w}x{h}", 
            f'{data["attributes"]["artwork"]["width"]}x{data["attributes"]["artwork"]["height"]}'
        )

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Artist name={self.name} id={self.id} "
            f"tracks={self.tracks}>"
        )