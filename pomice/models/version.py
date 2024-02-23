from typing import NamedTuple


class LavalinkVersion(NamedTuple):
    major: int
    minor: int
    fix: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return (
            (self.major == other.major) and (self.minor == other.minor) and (self.fix == other.fix)
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        if self.major > other.major:
            return False
        if self.minor > other.minor:
            return False
        if self.fix > other.fix:
            return False
        return True
