from typing import Literal, NamedTuple, Union

__all__ = ("LavalinkVersion",)


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


class LavalinkVersion3Type(LavalinkVersion):
    major: Literal[3]
    minor: int
    fix: int


class LavalinkVersion4Type(LavalinkVersion):
    major: Literal[4]
    minor: int
    fix: int


LavalinkVersionType = Union[LavalinkVersion3Type, LavalinkVersion4Type, LavalinkVersion]
