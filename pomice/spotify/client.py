from __future__ import annotations

import asyncio
import logging
import re
import time
from base64 import b64encode
from typing import AsyncGenerator
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import quote

import aiohttp
import orjson as json

from .exceptions import InvalidSpotifyURL
from .exceptions import SpotifyRequestException
from .objects import *

__all__ = ("Client",)


GRANT_URL = "https://accounts.spotify.com/api/token"
REQUEST_URL = "https://api.spotify.com/v1/{type}s/{id}"
# Keep this in sync with URLRegex.SPOTIFY_URL (enums.py). Accept intl locale segment,
# optional trailing slash, and query parameters.
SPOTIFY_URL_REGEX = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-zA-Z-]+/)?(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)(?:/)?(?:\?.*)?$",
)


class Client:
    """The base client for the Spotify module of Pomice.
    This class will do all the heavy lifting of getting all the metadata
    for any Spotify URL you throw at it.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        playlist_concurrency: int = 10,
        playlist_page_limit: Optional[int] = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

        # HTTP session will be injected by Node
        self.session: Optional[aiohttp.ClientSession] = None

        self._bearer_token: Optional[str] = None
        self._expiry: float = 0.0
        self._auth_token = b64encode(f"{self._client_id}:{self._client_secret}".encode())
        self._grant_headers = {"Authorization": f"Basic {self._auth_token.decode()}"}
        self._bearer_headers: Optional[Dict] = None
        self._log = logging.getLogger(__name__)

        # Performance tuning knobs
        self._playlist_concurrency = max(1, playlist_concurrency)
        self._playlist_page_limit = playlist_page_limit

    async def _set_session(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def _fetch_bearer_token(self) -> None:
        _data = {"grant_type": "client_credentials"}

        if not self.session:
            raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
        resp = await self.session.post(GRANT_URL, data=_data, headers=self._grant_headers)

        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error fetching bearer token: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        if self._log:
            self._log.debug(f"Fetched Spotify bearer token successfully")

        self._bearer_token = data["access_token"]
        self._expiry = time.time() + (int(data["expires_in"]) - 10)
        self._bearer_headers = {
            "Authorization": f"Bearer {self._bearer_token}",
        }

    async def search(self, *, query: str) -> Union[Track, Album, Artist, Playlist]:
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        if not result:
            raise InvalidSpotifyURL("The Spotify link provided is not valid.")

        spotify_type = result.group("type")
        spotify_id = result.group("id")

        request_url = REQUEST_URL.format(type=spotify_type, id=spotify_id)

        if not self.session:
            raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        if self._log:
            self._log.debug(
                f"Made request to Spotify API with status {resp.status} and response {data}",
            )

        if spotify_type == "track":
            return Track(data)
        elif spotify_type == "album":
            return Album(data)
        elif spotify_type == "artist":
            if not self.session:
                raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
            resp = await self.session.get(
                f"{request_url}/top-tracks?market=US",
                headers=self._bearer_headers,
            )
            if resp.status != 200:
                raise SpotifyRequestException(
                    f"Error while fetching results: {resp.status} {resp.reason}",
                )

            track_data: dict = await resp.json(loads=json.loads)
            tracks = track_data["tracks"]
            return Artist(data, tracks)
        else:
            # For playlists we optionally use a reduced fields payload to shrink response sizes.
            # NB: We cannot apply fields filter to initial request because original metadata is needed.
            tracks = [
                Track(track["track"])
                for track in data["tracks"]["items"]
                if track["track"] is not None
            ]

            if not tracks:
                raise SpotifyRequestException(
                    "This playlist is empty and therefore cannot be queued.",
                )

            total_tracks = data["tracks"]["total"]
            limit = data["tracks"]["limit"]

            # Short‑circuit small playlists (single page)
            if total_tracks <= limit:
                return Playlist(data, tracks)

            # Build remaining page URLs; Spotify supports offset-based pagination.
            remaining_offsets = range(limit, total_tracks, limit)
            page_urls: List[str] = []
            fields_filter = (
                "items(track(name,duration_ms,id,is_local,external_urls,external_ids,artists(name),album(images)))"
                ",next"
            )
            for idx, offset in enumerate(remaining_offsets):
                if self._playlist_page_limit is not None and idx >= self._playlist_page_limit:
                    break
                page_urls.append(
                    f"{request_url}/tracks?offset={offset}&limit={limit}&fields={quote(fields_filter)}",
                )

            if page_urls:
                semaphore = asyncio.Semaphore(self._playlist_concurrency)

                async def fetch_page(url: str) -> Optional[List[Track]]:
                    async with semaphore:
                        if not self.session:
                            raise SpotifyRequestException(
                                "HTTP session not initialized for Spotify client.",
                            )
                        resp = await self.session.get(url, headers=self._bearer_headers)
                        if resp.status != 200:
                            if self._log:
                                self._log.warning(
                                    f"Page fetch failed {resp.status} {resp.reason} for {url}",
                                )
                            return None
                        page_json: dict = await resp.json(loads=json.loads)
                        return [
                            Track(item["track"])
                            for item in page_json.get("items", [])
                            if item.get("track") is not None
                        ]

                # Chunk gather in waves to avoid creating thousands of tasks at once
                aggregated: List[Track] = []
                wave_size = self._playlist_concurrency * 2
                for i in range(0, len(page_urls), wave_size):
                    wave = page_urls[i : i + wave_size]
                    results = await asyncio.gather(
                        *[fetch_page(url) for url in wave],
                        return_exceptions=False,
                    )
                    for result in results:
                        if result:
                            aggregated.extend(result)

                tracks.extend(aggregated)

            return Playlist(data, tracks)

    async def iter_playlist_tracks(
        self,
        *,
        query: str,
        batch_size: int = 100,
    ) -> AsyncGenerator[List[Track], None]:
        """Stream playlist tracks in batches without waiting for full materialization.

        Parameters
        ----------
        query: str
            Spotify playlist URL.
        batch_size: int
            Number of tracks yielded per batch (logical grouping after fetch). Does not alter API page size.
        """
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        match = SPOTIFY_URL_REGEX.match(query)
        if not match or match.group("type") != "playlist":
            raise InvalidSpotifyURL("Provided query is not a valid Spotify playlist URL.")

        playlist_id = match.group("id")
        request_url = REQUEST_URL.format(type="playlist", id=playlist_id)
        if not self.session:
            raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )
        data: dict = await resp.json(loads=json.loads)

        # Yield first page immediately
        first_page_tracks = [
            Track(item["track"])
            for item in data["tracks"]["items"]
            if item.get("track") is not None
        ]
        # Batch yield
        for i in range(0, len(first_page_tracks), batch_size):
            yield first_page_tracks[i : i + batch_size]

        total = data["tracks"]["total"]
        limit = data["tracks"]["limit"]
        remaining_offsets = range(limit, total, limit)
        fields_filter = (
            "items(track(name,duration_ms,id,is_local,external_urls,external_ids,artists(name),album(images)))"
            ",next"
        )

        semaphore = asyncio.Semaphore(self._playlist_concurrency)

        async def fetch(offset: int) -> List[Track]:
            url = (
                f"{request_url}/tracks?offset={offset}&limit={limit}&fields={quote(fields_filter)}"
            )
            async with semaphore:
                if not self.session:
                    raise SpotifyRequestException(
                        "HTTP session not initialized for Spotify client.",
                    )
                r = await self.session.get(url, headers=self._bearer_headers)
                if r.status != 200:
                    if self._log:
                        self._log.warning(
                            f"Skipping page offset={offset} due to {r.status} {r.reason}",
                        )
                    return []
                pj: dict = await r.json(loads=json.loads)
                return [
                    Track(item["track"])
                    for item in pj.get("items", [])
                    if item.get("track") is not None
                ]

        # Fetch pages in rolling waves; yield promptly as soon as a wave completes.
        wave_size = self._playlist_concurrency * 2
        remaining_offsets_list = list(remaining_offsets)

        for i in range(0, len(remaining_offsets_list), wave_size):
            wave_offsets = remaining_offsets_list[i : i + wave_size]
            results = await asyncio.gather(*[fetch(o) for o in wave_offsets])
            for page_tracks in results:
                if not page_tracks:
                    continue
                for j in range(0, len(page_tracks), batch_size):
                    yield page_tracks[j : j + batch_size]

    async def get_recommendations(self, *, query: str) -> List[Track]:
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        result = SPOTIFY_URL_REGEX.match(query)
        if not result:
            raise InvalidSpotifyURL("The Spotify link provided is not valid.")

        spotify_type = result.group("type")
        spotify_id = result.group("id")

        if not spotify_type == "track":
            raise InvalidSpotifyURL(
                "The provided query is not a Spotify track.",
            )

        request_url = REQUEST_URL.format(
            type="recommendation",
            id=f"?seed_tracks={spotify_id}",
        )

        if not self.session:
            raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        tracks = [Track(track) for track in data["tracks"]]

        return tracks

    async def track_search(self, *, query: str) -> List[Track]:
        if not self._bearer_token or time.time() >= self._expiry:
            await self._fetch_bearer_token()

        request_url = f"https://api.spotify.com/v1/search?q={quote(query)}&type=track"

        if not self.session:
            raise SpotifyRequestException("HTTP session not initialized for Spotify client.")
        resp = await self.session.get(request_url, headers=self._bearer_headers)
        if resp.status != 200:
            raise SpotifyRequestException(
                f"Error while fetching results: {resp.status} {resp.reason}",
            )

        data: dict = await resp.json(loads=json.loads)
        tracks = [Track(track) for track in data["tracks"]["items"]]

        return tracks
