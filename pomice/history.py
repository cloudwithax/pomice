from __future__ import annotations

from collections import deque
from typing import Deque
from typing import Iterator
from typing import List
from typing import Optional

from .objects import Track

__all__ = ("TrackHistory",)


class TrackHistory:
    """Track history manager for Pomice.

    Keeps track of previously played tracks with a configurable maximum size.
    Useful for implementing 'previous track' functionality and viewing play history.
    """

    __slots__ = ("_history", "max_size", "_current_index")

    def __init__(self, max_size: int = 100) -> None:
        """Initialize the track history.

        Parameters
        ----------
        max_size: int
            Maximum number of tracks to keep in history. Defaults to 100.
        """
        self.max_size = max_size
        self._history: Deque[Track] = deque(maxlen=max_size)
        self._current_index: int = -1

    def __len__(self) -> int:
        """Return the number of tracks in history."""
        return len(self._history)

    def __bool__(self) -> bool:
        """Return True if history contains tracks."""
        return bool(self._history)

    def __iter__(self) -> Iterator[Track]:
        """Iterate over tracks in history (newest to oldest)."""
        return reversed(self._history)

    def __getitem__(self, index: int) -> Track:
        """Get a track at the given index in history.

        Parameters
        ----------
        index: int
            Index of the track (0 = most recent)
        """
        return self._history[-(index + 1)]

    def __repr__(self) -> str:
        return f"<Pomice.TrackHistory size={len(self._history)} max_size={self.max_size}>"

    def add(self, track: Track) -> None:
        """Add a track to the history.

        Parameters
        ----------
        track: Track
            The track to add to history
        """
        self._history.append(track)
        self._current_index = len(self._history) - 1

    def get_last(self, count: int = 1) -> List[Track]:
        """Get the last N tracks from history.

        Parameters
        ----------
        count: int
            Number of tracks to retrieve. Defaults to 1.

        Returns
        -------
        List[Track]
            List of the last N tracks (most recent first)
        """
        if count <= 0:
            return []
        return list(reversed(list(self._history)[-count:]))

    def get_previous(self) -> Optional[Track]:
        """Get the previous track in history.

        Returns
        -------
        Optional[Track]
            The previous track, or None if at the beginning
        """
        if not self._history or self._current_index <= 0:
            return None

        self._current_index -= 1
        return self._history[self._current_index]

    def get_next(self) -> Optional[Track]:
        """Get the next track in history (when navigating backwards).

        Returns
        -------
        Optional[Track]
            The next track, or None if at the end
        """
        if not self._history or self._current_index >= len(self._history) - 1:
            return None

        self._current_index += 1
        return self._history[self._current_index]

    def clear(self) -> None:
        """Clear all tracks from history."""
        self._history.clear()
        self._current_index = -1

    def get_all(self) -> List[Track]:
        """Get all tracks in history.

        Returns
        -------
        List[Track]
            All tracks in history (most recent first)
        """
        return list(reversed(self._history))

    def search(self, query: str) -> List[Track]:
        """Search for tracks in history by title or author.

        Parameters
        ----------
        query: str
            Search query (case-insensitive)

        Returns
        -------
        List[Track]
            Matching tracks (most recent first)
        """
        query_lower = query.lower()
        return [
            track
            for track in reversed(self._history)
            if query_lower in track.title.lower() or query_lower in track.author.lower()
        ]

    def get_unique_tracks(self) -> List[Track]:
        """Get unique tracks from history (removes duplicates).

        Returns
        -------
        List[Track]
            Unique tracks (most recent occurrence kept)
        """
        seen = set()
        unique = []
        for track in reversed(self._history):
            if track.track_id not in seen:
                seen.add(track.track_id)
                unique.append(track)
        return unique

    def get_by_requester(self, requester_id: int) -> List[Track]:
        """Get all tracks requested by a specific user.

        Parameters
        ----------
        requester_id: int
            Discord user ID

        Returns
        -------
        List[Track]
            Tracks requested by the user (most recent first)
        """
        return [
            track
            for track in reversed(self._history)
            if track.requester and track.requester.id == requester_id
        ]

    @property
    def is_empty(self) -> bool:
        """Check if history is empty."""
        return len(self._history) == 0

    @property
    def current(self) -> Optional[Track]:
        """Get the current track in navigation."""
        if not self._history or self._current_index < 0:
            return None
        return self._history[self._current_index]
