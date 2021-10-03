from .exceptions import FilterInvalidArgument


class Filter:
    def __init__(self):
        self.payload = None


class Timescale(Filter):
    """Filter which changes the speed and pitch of a track.
       Do be warned that this filter is bugged as of the lastest Lavalink dev version
       due to the filter patch not corresponding with the track time.

       In short this means that your track will either end prematurely or end later due to this.
       This is not the library's fault.
    """

    def __init__(self, *, speed: float = 1.0, pitch: float = 1.0, rate: float = 1.0):
        super().__init__()

        if speed < 0:
            raise FilterInvalidArgument("Timescale speed must be more than 0.")
        if pitch < 0:
            raise FilterInvalidArgument("Timescale pitch must be more than 0.")
        if rate < 0:
            raise FilterInvalidArgument("Timescale rate must be more than 0.")

        self.speed = speed
        self.pitch = pitch
        self.rate = rate

        self.payload = {"timescale": {"speed": self.speed,
                                      "pitch": self.pitch,
                                      "rate": self.rate}}

    def __repr__(self):
        return f"<Pomice.TimescaleFilter speed={self.speed} pitch={self.pitch} rate={self.rate}>"


class Karaoke(Filter):
    """Filter which filters the vocal track from any song and leaves the instrumental.
       Best for karaoke as the filter implies.
    """

    def __init__(
        self,
        *,
        level: float,
        mono_level: float,
        filter_band: float,
        filter_width: float
    ):
        super().__init__()

        self.level = level
        self.mono_level = mono_level
        self.filter_band = filter_band
        self.filter_width = filter_width

        self.payload = {"karaoke": {"level": self.level,
                                    "monoLevel": self.mono_level,
                                    "filterBand": self.filter_band,
                                    "filterWidth": self.filter_width}}

    def __repr__(self):
        return (
            f"<Pomice.KaraokeFilter level={self.level} mono_level={self.mono_level} "
            f"filter_band={self.filter_band} filter_width={self.filter_width}>"
        )


class Tremolo(Filter):
    """Filter which produces a wavering tone in the music,
       causing it to sound like the music is changing in volume rapidly.
    """

    def __init__(self, *, frequency: float, depth: float):
        super().__init__()

        if frequency < 0:
            raise FilterInvalidArgument("Tremolo frequency must be more than 0.")
        if depth < 0 or depth > 1:
            raise FilterInvalidArgument("Tremolo depth must be between 0 and 1.")

        self.frequency = frequency
        self.depth = depth

        self.payload = {"tremolo": {"frequency": self.frequency,
                                    "depth": self.depth}}

    def __repr__(self):
        return f"<Pomice.TremoloFilter frequency={self.frequency} depth={self.depth}>"


class Vibrato(Filter):
    """Filter which produces a wavering tone in the music, similar to the Tremolo filter,
       but changes in pitch rather than volume.
    """

    def __init__(self, *, frequency: float, depth: float):

        super().__init__()
        if frequency < 0 or frequency > 14:
            raise FilterInvalidArgument("Vibrato frequency must be between 0 and 14.")
        if depth < 0 or depth > 1:
            raise FilterInvalidArgument("Vibrato depth must be between 0 and 1.")

        self.frequency = frequency
        self.depth = depth

        self.payload = {"vibrato": {"frequency": self.frequency,
                                    "depth": self.depth}}

    def __repr__(self):
        return f"<Pomice.VibratoFilter frequency={self.frequency} depth={self.depth}>"
