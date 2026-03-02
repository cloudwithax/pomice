from __future__ import annotations

from collections import Counter
from typing import Dict
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .objects import Track
    from .queue import Queue

__all__ = ("QueueStats",)


class QueueStats:
    """Advanced statistics for a Pomice Queue.

    Provides detailed analytics about queue contents including duration,
    requester statistics, and track distribution.
    """

    def __init__(self, queue: Queue) -> None:
        """Initialize queue statistics.

        Parameters
        ----------
        queue: Queue
            The queue to analyze
        """
        self._queue = queue

    @property
    def total_duration(self) -> int:
        """Get total duration of all tracks in queue (milliseconds).

        Returns
        -------
        int
            Total duration in milliseconds
        """
        return sum(track.length for track in self._queue)

    @property
    def average_duration(self) -> float:
        """Get average track duration in queue (milliseconds).

        Returns
        -------
        float
            Average duration in milliseconds, or 0.0 if queue is empty
        """
        if self._queue.is_empty:
            return 0.0
        return self.total_duration / len(self._queue)

    @property
    def longest_track(self) -> Optional[Track]:
        """Get the longest track in the queue.

        Returns
        -------
        Optional[Track]
            The longest track, or None if queue is empty
        """
        if self._queue.is_empty:
            return None
        return max(self._queue, key=lambda t: t.length)

    @property
    def shortest_track(self) -> Optional[Track]:
        """Get the shortest track in the queue.

        Returns
        -------
        Optional[Track]
            The shortest track, or None if queue is empty
        """
        if self._queue.is_empty:
            return None
        return min(self._queue, key=lambda t: t.length)

    def get_requester_stats(self) -> Dict[int, Dict[str, any]]:
        """Get statistics grouped by requester.

        Returns
        -------
        Dict[int, Dict[str, any]]
            Dictionary mapping user IDs to their stats:
            - 'count': Number of tracks requested
            - 'total_duration': Total duration of their tracks (ms)
            - 'tracks': List of their tracks
        """
        stats: Dict[int, Dict] = {}

        for track in self._queue:
            if not track.requester:
                continue

            user_id = track.requester.id
            if user_id not in stats:
                stats[user_id] = {
                    "count": 0,
                    "total_duration": 0,
                    "tracks": [],
                    "requester": track.requester,
                }

            stats[user_id]["count"] += 1
            stats[user_id]["total_duration"] += track.length
            stats[user_id]["tracks"].append(track)

        return stats

    def get_top_requesters(self, limit: int = 5) -> List[tuple]:
        """Get top requesters by track count.

        Parameters
        ----------
        limit: int
            Maximum number of requesters to return. Defaults to 5.

        Returns
        -------
        List[tuple]
            List of (requester, count) tuples sorted by count (descending)
        """
        requester_counts = Counter(track.requester.id for track in self._queue if track.requester)

        # Get requester objects
        stats = self.get_requester_stats()
        return [
            (stats[user_id]["requester"], count)
            for user_id, count in requester_counts.most_common(limit)
        ]

    def get_author_distribution(self) -> Dict[str, int]:
        """Get distribution of tracks by author.

        Returns
        -------
        Dict[str, int]
            Dictionary mapping author names to track counts
        """
        return dict(Counter(track.author for track in self._queue))

    def get_top_authors(self, limit: int = 10) -> List[tuple]:
        """Get most common authors in the queue.

        Parameters
        ----------
        limit: int
            Maximum number of authors to return. Defaults to 10.

        Returns
        -------
        List[tuple]
            List of (author, count) tuples sorted by count (descending)
        """
        author_counts = Counter(track.author for track in self._queue)
        return author_counts.most_common(limit)

    def get_stream_count(self) -> int:
        """Get count of streams in the queue.

        Returns
        -------
        int
            Number of streams
        """
        return sum(1 for track in self._queue if track.is_stream)

    def get_playlist_distribution(self) -> Dict[str, int]:
        """Get distribution of tracks by playlist.

        Returns
        -------
        Dict[str, int]
            Dictionary mapping playlist names to track counts
        """
        distribution: Dict[str, int] = {}

        for track in self._queue:
            if track.playlist:
                playlist_name = track.playlist.name
                distribution[playlist_name] = distribution.get(playlist_name, 0) + 1

        return distribution

    def get_duration_breakdown(self) -> Dict[str, int]:
        """Get breakdown of tracks by duration categories.

        Returns
        -------
        Dict[str, int]
            Dictionary with counts for different duration ranges:
            - 'short' (< 3 min)
            - 'medium' (3-6 min)
            - 'long' (6-10 min)
            - 'very_long' (> 10 min)
        """
        breakdown = {
            "short": 0,  # < 3 minutes
            "medium": 0,  # 3-6 minutes
            "long": 0,  # 6-10 minutes
            "very_long": 0,  # > 10 minutes
        }

        for track in self._queue:
            duration_minutes = track.length / 60000  # Convert ms to minutes

            if duration_minutes < 3:
                breakdown["short"] += 1
            elif duration_minutes < 6:
                breakdown["medium"] += 1
            elif duration_minutes < 10:
                breakdown["long"] += 1
            else:
                breakdown["very_long"] += 1

        return breakdown

    def format_duration(self, milliseconds: int) -> str:
        """Format duration in milliseconds to human-readable string.

        Parameters
        ----------
        milliseconds: int
            Duration in milliseconds

        Returns
        -------
        str
            Formatted duration (e.g., "1:23:45" or "5:30")
        """
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def get_summary(self) -> Dict[str, any]:
        """Get a comprehensive summary of queue statistics.

        Returns
        -------
        Dict[str, any]
            Dictionary containing various queue statistics
        """
        return {
            "total_tracks": len(self._queue),
            "total_duration": self.total_duration,
            "total_duration_formatted": self.format_duration(self.total_duration),
            "average_duration": self.average_duration,
            "average_duration_formatted": self.format_duration(int(self.average_duration)),
            "longest_track": self.longest_track,
            "shortest_track": self.shortest_track,
            "stream_count": self.get_stream_count(),
            "unique_authors": len(self.get_author_distribution()),
            "unique_requesters": len(self.get_requester_stats()),
            "duration_breakdown": self.get_duration_breakdown(),
            "loop_mode": self._queue.loop_mode,
            "is_looping": self._queue.is_looping,
        }

    def __repr__(self) -> str:
        return (
            f"<Pomice.QueueStats tracks={len(self._queue)} "
            f"duration={self.format_duration(self.total_duration)}>"
        )
