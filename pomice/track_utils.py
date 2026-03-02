from __future__ import annotations

from typing import Callable
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .objects import Track

__all__ = ("TrackFilter", "SearchHelper")


class TrackFilter:
    """Advanced filtering utilities for tracks.

    Provides various filter functions to find tracks matching specific criteria.
    """

    @staticmethod
    def by_duration(
        tracks: List[Track],
        *,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
    ) -> List[Track]:
        """Filter tracks by duration range.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        min_duration: Optional[int]
            Minimum duration in milliseconds
        max_duration: Optional[int]
            Maximum duration in milliseconds

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        result = tracks

        if min_duration is not None:
            result = [t for t in result if t.length >= min_duration]

        if max_duration is not None:
            result = [t for t in result if t.length <= max_duration]

        return result

    @staticmethod
    def by_author(tracks: List[Track], author: str, *, exact: bool = False) -> List[Track]:
        """Filter tracks by author name.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        author: str
            Author name to search for
        exact: bool
            Whether to match exactly. Defaults to False (case-insensitive contains).

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        if exact:
            return [t for t in tracks if t.author == author]

        author_lower = author.lower()
        return [t for t in tracks if author_lower in t.author.lower()]

    @staticmethod
    def by_title(tracks: List[Track], title: str, *, exact: bool = False) -> List[Track]:
        """Filter tracks by title.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        title: str
            Title to search for
        exact: bool
            Whether to match exactly. Defaults to False (case-insensitive contains).

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        if exact:
            return [t for t in tracks if t.title == title]

        title_lower = title.lower()
        return [t for t in tracks if title_lower in t.title.lower()]

    @staticmethod
    def by_requester(tracks: List[Track], requester_id: int) -> List[Track]:
        """Filter tracks by requester.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        requester_id: int
            Discord user ID

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        return [t for t in tracks if t.requester and t.requester.id == requester_id]

    @staticmethod
    def by_playlist(tracks: List[Track], playlist_name: str) -> List[Track]:
        """Filter tracks by playlist name.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        playlist_name: str
            Playlist name to search for

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        playlist_lower = playlist_name.lower()
        return [t for t in tracks if t.playlist and playlist_lower in t.playlist.name.lower()]

    @staticmethod
    def streams_only(tracks: List[Track]) -> List[Track]:
        """Filter to only include streams.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter

        Returns
        -------
        List[Track]
            Only stream tracks
        """
        return [t for t in tracks if t.is_stream]

    @staticmethod
    def non_streams_only(tracks: List[Track]) -> List[Track]:
        """Filter to exclude streams.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter

        Returns
        -------
        List[Track]
            Only non-stream tracks
        """
        return [t for t in tracks if not t.is_stream]

    @staticmethod
    def custom(tracks: List[Track], predicate: Callable[[Track], bool]) -> List[Track]:
        """Filter tracks using a custom predicate function.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to filter
        predicate: Callable[[Track], bool]
            Function that returns True for tracks to include

        Returns
        -------
        List[Track]
            Filtered tracks
        """
        return [t for t in tracks if predicate(t)]


class SearchHelper:
    """Helper utilities for searching and sorting tracks."""

    @staticmethod
    def search_tracks(
        tracks: List[Track],
        query: str,
        *,
        search_title: bool = True,
        search_author: bool = True,
        case_sensitive: bool = False,
    ) -> List[Track]:
        """Search tracks by query string.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to search
        query: str
            Search query
        search_title: bool
            Whether to search in titles. Defaults to True.
        search_author: bool
            Whether to search in authors. Defaults to True.
        case_sensitive: bool
            Whether search is case-sensitive. Defaults to False.

        Returns
        -------
        List[Track]
            Matching tracks
        """
        if not case_sensitive:
            query = query.lower()

        results = []
        for track in tracks:
            title = track.title if case_sensitive else track.title.lower()
            author = track.author if case_sensitive else track.author.lower()

            if search_title and query in title:
                results.append(track)
            elif search_author and query in author:
                results.append(track)

        return results

    @staticmethod
    def sort_by_duration(
        tracks: List[Track],
        *,
        reverse: bool = False,
    ) -> List[Track]:
        """Sort tracks by duration.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to sort
        reverse: bool
            If True, sort longest to shortest. Defaults to False.

        Returns
        -------
        List[Track]
            Sorted tracks
        """
        return sorted(tracks, key=lambda t: t.length, reverse=reverse)

    @staticmethod
    def sort_by_title(
        tracks: List[Track],
        *,
        reverse: bool = False,
    ) -> List[Track]:
        """Sort tracks alphabetically by title.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to sort
        reverse: bool
            If True, sort Z to A. Defaults to False.

        Returns
        -------
        List[Track]
            Sorted tracks
        """
        return sorted(tracks, key=lambda t: t.title.lower(), reverse=reverse)

    @staticmethod
    def sort_by_author(
        tracks: List[Track],
        *,
        reverse: bool = False,
    ) -> List[Track]:
        """Sort tracks alphabetically by author.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to sort
        reverse: bool
            If True, sort Z to A. Defaults to False.

        Returns
        -------
        List[Track]
            Sorted tracks
        """
        return sorted(tracks, key=lambda t: t.author.lower(), reverse=reverse)

    @staticmethod
    def remove_duplicates(
        tracks: List[Track],
        *,
        by_uri: bool = True,
        by_title_author: bool = False,
    ) -> List[Track]:
        """Remove duplicate tracks from a list.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks
        by_uri: bool
            Remove duplicates by URI. Defaults to True.
        by_title_author: bool
            Remove duplicates by title+author combination. Defaults to False.

        Returns
        -------
        List[Track]
            List with duplicates removed (keeps first occurrence)
        """
        seen = set()
        result = []

        for track in tracks:
            if by_uri:
                key = track.uri
            elif by_title_author:
                key = (track.title.lower(), track.author.lower())
            else:
                key = track.track_id

            if key not in seen:
                seen.add(key)
                result.append(track)

        return result

    @staticmethod
    def group_by_author(tracks: List[Track]) -> dict[str, List[Track]]:
        """Group tracks by author.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to group

        Returns
        -------
        dict[str, List[Track]]
            Dictionary mapping author names to their tracks
        """
        groups = {}
        for track in tracks:
            author = track.author
            if author not in groups:
                groups[author] = []
            groups[author].append(track)
        return groups

    @staticmethod
    def group_by_playlist(tracks: List[Track]) -> dict[str, List[Track]]:
        """Group tracks by playlist.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to group

        Returns
        -------
        dict[str, List[Track]]
            Dictionary mapping playlist names to their tracks
        """
        groups = {}
        for track in tracks:
            if track.playlist:
                playlist_name = track.playlist.name
                if playlist_name not in groups:
                    groups[playlist_name] = []
                groups[playlist_name].append(track)
        return groups

    @staticmethod
    def get_random_tracks(tracks: List[Track], count: int) -> List[Track]:
        """Get random tracks from a list.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks
        count: int
            Number of random tracks to get

        Returns
        -------
        List[Track]
            Random tracks (without replacement)
        """
        import random

        return random.sample(tracks, min(count, len(tracks)))
