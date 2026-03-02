from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .objects import Track
    from .queue import Queue

__all__ = ("PlaylistManager",)


class PlaylistManager:
    """Manager for exporting and importing playlists.

    Allows saving queue contents to JSON files and loading them back,
    useful for persistent playlists and sharing.
    """

    @staticmethod
    def export_queue(
        queue: Queue,
        filepath: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        include_metadata: bool = True,
    ) -> None:
        """Export a queue to a JSON file.

        Parameters
        ----------
        queue: Queue
            The queue to export
        filepath: str
            Path to save the JSON file
        name: Optional[str]
            Name for the playlist. Defaults to filename.
        description: Optional[str]
            Description for the playlist
        include_metadata: bool
            Whether to include requester and timestamp metadata. Defaults to True.
        """
        path = Path(filepath)

        if name is None:
            name = path.stem

        tracks_data = []
        for track in queue:
            track_dict = {
                "title": track.title,
                "author": track.author,
                "uri": track.uri,
                "identifier": track.identifier,
                "length": track.length,
                "is_stream": track.is_stream,
            }

            if include_metadata:
                track_dict["requester_id"] = track.requester.id if track.requester else None
                track_dict["requester_name"] = str(track.requester) if track.requester else None
                track_dict["timestamp"] = track.timestamp

            if track.thumbnail:
                track_dict["thumbnail"] = track.thumbnail

            if track.isrc:
                track_dict["isrc"] = track.isrc

            if track.playlist:
                track_dict["playlist_name"] = track.playlist.name

            tracks_data.append(track_dict)

        playlist_data = {
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "track_count": len(tracks_data),
            "total_duration": sum(t["length"] for t in tracks_data),
            "tracks": tracks_data,
            "version": "1.0",
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(playlist_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def import_playlist(filepath: str) -> Dict[str, Any]:
        """Import a playlist from a JSON file.

        Parameters
        ----------
        filepath: str
            Path to the JSON file

        Returns
        -------
        Dict[str, Any]
            Dictionary containing playlist data:
            - 'name': Playlist name
            - 'description': Playlist description
            - 'tracks': List of track data dictionaries
            - 'track_count': Number of tracks
            - 'total_duration': Total duration in milliseconds
            - 'created_at': Creation timestamp
        """
        path = Path(filepath)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return data

    @staticmethod
    def export_track_list(
        tracks: List[Track],
        filepath: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Export a list of tracks to a JSON file.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to export
        filepath: str
            Path to save the JSON file
        name: Optional[str]
            Name for the playlist
        description: Optional[str]
            Description for the playlist
        """
        path = Path(filepath)

        if name is None:
            name = path.stem

        tracks_data = [
            {
                "title": track.title,
                "author": track.author,
                "uri": track.uri,
                "identifier": track.identifier,
                "length": track.length,
                "thumbnail": track.thumbnail,
                "isrc": track.isrc,
            }
            for track in tracks
        ]

        playlist_data = {
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "track_count": len(tracks_data),
            "total_duration": sum(t["length"] for t in tracks_data),
            "tracks": tracks_data,
            "version": "1.0",
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(playlist_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def get_track_uris(filepath: str) -> List[str]:
        """Get list of track URIs from a saved playlist.

        Parameters
        ----------
        filepath: str
            Path to the JSON file

        Returns
        -------
        List[str]
            List of track URIs
        """
        data = PlaylistManager.import_playlist(filepath)
        return [track["uri"] for track in data["tracks"] if track.get("uri")]

    @staticmethod
    def merge_playlists(
        filepaths: List[str],
        output_path: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        remove_duplicates: bool = True,
    ) -> None:
        """Merge multiple playlists into one.

        Parameters
        ----------
        filepaths: List[str]
            List of playlist file paths to merge
        output_path: str
            Path to save the merged playlist
        name: Optional[str]
            Name for the merged playlist
        description: Optional[str]
            Description for the merged playlist
        remove_duplicates: bool
            Whether to remove duplicate tracks (by URI). Defaults to True.
        """
        all_tracks = []
        seen_uris = set()

        for filepath in filepaths:
            data = PlaylistManager.import_playlist(filepath)

            for track in data["tracks"]:
                uri = track.get("uri", "")

                if remove_duplicates:
                    if uri and uri in seen_uris:
                        continue
                    if uri:
                        seen_uris.add(uri)

                all_tracks.append(track)

        merged_data = {
            "name": name or "Merged Playlist",
            "description": description or f"Merged from {len(filepaths)} playlists",
            "created_at": datetime.utcnow().isoformat(),
            "track_count": len(all_tracks),
            "total_duration": sum(t["length"] for t in all_tracks),
            "tracks": all_tracks,
            "version": "1.0",
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def export_to_m3u(
        tracks: List[Track],
        filepath: str,
        *,
        name: Optional[str] = None,
    ) -> None:
        """Export tracks to M3U playlist format.

        Parameters
        ----------
        tracks: List[Track]
            List of tracks to export
        filepath: str
            Path to save the M3U file
        name: Optional[str]
            Playlist name for the header
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            if name:
                f.write(f"#PLAYLIST:{name}\n")

            for track in tracks:
                # Duration in seconds
                duration = track.length // 1000
                f.write(f"#EXTINF:{duration},{track.author} - {track.title}\n")
                f.write(f"{track.uri}\n")

    @staticmethod
    def get_playlist_info(filepath: str) -> Dict[str, Any]:
        """Get basic information about a saved playlist without loading all tracks.

        Parameters
        ----------
        filepath: str
            Path to the JSON file

        Returns
        -------
        Dict[str, Any]
            Dictionary with playlist metadata (name, track_count, duration, etc.)
        """
        data = PlaylistManager.import_playlist(filepath)

        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "track_count": data.get("track_count"),
            "total_duration": data.get("total_duration"),
            "created_at": data.get("created_at"),
            "version": data.get("version"),
        }
