class Song:
    def  __init__(self, data: dict) -> None:
        self.track_data = ["data"][0]
        self.name = self.track_data["attributes"]["name"]
        self.url = self.track_data["atrributes"]["url"]
        self.isrc = self.track_data["atrributes"]["isrc"]
        self.length = self.track_data["atrributes"]["durationInMillis"]
        self.id = self.track_data["id"]
        self.artists = self.track_data["atrributes"]["artistName"]
        self.image = self.track_data["atrributes"]["artwork"]["url"].replace("{w}x{h}", f'{self.track_data["atrributes"]["artwork"]["width"]}x{self.track_data["atrributes"]["artwork"]["height"]}')

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Track name={self.name} artists={self.artists} "
            f"length={self.length} id={self.id} isrc={self.isrc}>"
        )
   

class Playlist:
    def __init__(self, data: dict) -> None:
        pass

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Playlist name={self.name} owner={self.owner} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )

             
class Album:
    def __init__(self, data: dict) -> None:
        pass

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Album name={self.name} artists={self.artists} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )
        


class Artist:
    def __init__(self, data: dict) -> None:
        pass

    def __repr__(self) -> str:
        return (
            f"<Pomice.applemusic.Artist name={self.name} id={self.id} "
            f"tracks={self.tracks}>"
        )