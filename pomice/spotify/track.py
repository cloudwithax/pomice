class Track:
    """The base class for a Spotify Track"""

    def __init__(self, data: dict) -> None:
        self.name = data['name']
        self.artists = ", ".join(artist["name"] for artist in data['artists'])
        self.length = data['duration_ms']
        self.id = data['id']

        if data.get("album") and data["album"]["images"]:
            self.image = data['album']['images'][0]['url']
        else:
            self.image = None

        self.uri = data['external_urls']['spotify']

    def __repr__(self) -> str:
        return f"<Pomice.spotify.Track name={self.name} artists={self.artists} length={self.length} id={self.id}>"
