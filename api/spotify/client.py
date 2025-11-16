"""Spotify Web API client implementation.

Spotify API Documentation: https://developer.spotify.com/documentation/web-api
Authentication: Client Credentials Flow (server-to-server)
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# Music Data Classes
# ============================================================================

@dataclass(slots=True, frozen=True)
class SpotifyArtist:
    """Represents a Spotify artist."""
    
    id: str
    name: str
    uri: str
    external_urls: dict[str, str]
    genres: list[str]
    popularity: Optional[int] = None
    followers: Optional[int] = None
    images: Optional[list[dict[str, Any]]] = None


@dataclass(slots=True, frozen=True)
class SpotifyAlbum:
    """Represents a Spotify album."""
    
    id: str
    name: str
    uri: str
    album_type: str  # album, single, compilation
    release_date: str
    release_date_precision: str  # year, month, day
    total_tracks: int
    external_urls: dict[str, str]
    images: list[dict[str, Any]]
    artists: list[dict[str, str]]  # Simplified artist info
    genres: Optional[list[str]] = None
    label: Optional[str] = None
    popularity: Optional[int] = None
    copyrights: Optional[list[dict[str, str]]] = None


@dataclass(slots=True, frozen=True)
class SpotifyTrack:
    """Represents a Spotify track with full details."""
    
    id: str
    name: str
    uri: str
    duration_ms: int
    explicit: bool
    external_urls: dict[str, str]
    external_ids: dict[str, str]  # isrc, ean, upc
    preview_url: Optional[str]
    track_number: int
    disc_number: int
    popularity: int
    artists: list[dict[str, Any]]
    album: dict[str, Any]  # Simplified album info
    available_markets: list[str]
    is_local: bool
    raw_data: dict[str, Any]  # Store complete response


@dataclass(slots=True, frozen=True)
class SpotifyAudioFeatures:
    """Represents audio analysis features for a track."""
    
    id: str
    acousticness: float  # 0.0 to 1.0
    danceability: float  # 0.0 to 1.0
    energy: float  # 0.0 to 1.0
    instrumentalness: float  # 0.0 to 1.0
    key: int  # -1 to 11 (pitch class notation)
    liveness: float  # 0.0 to 1.0
    loudness: float  # -60 to 0 dB
    mode: int  # 0 = minor, 1 = major
    speechiness: float  # 0.0 to 1.0
    tempo: float  # BPM
    time_signature: int  # 3 to 7
    valence: float  # 0.0 to 1.0 (musical positiveness)
    duration_ms: int


# ============================================================================
# Podcast Data Classes
# ============================================================================

@dataclass(slots=True, frozen=True)
class SpotifyShow:
    """Represents a Spotify podcast show."""
    
    id: str
    name: str
    uri: str
    description: str
    publisher: str
    external_urls: dict[str, str]
    images: list[dict[str, Any]]
    languages: list[str]
    media_type: str
    explicit: bool
    total_episodes: int
    copyrights: Optional[list[dict[str, str]]] = None
    html_description: Optional[str] = None
    is_externally_hosted: Optional[bool] = None
    raw_data: dict[str, Any] = None


@dataclass(slots=True, frozen=True)
class SpotifyEpisode:
    """Represents a Spotify podcast episode."""
    
    id: str
    name: str
    uri: str
    description: str
    duration_ms: int
    explicit: bool
    external_urls: dict[str, str]
    images: list[dict[str, Any]]
    release_date: str
    release_date_precision: str
    languages: list[str]
    audio_preview_url: Optional[str]
    html_description: Optional[str]
    show: dict[str, Any]  # Simplified show info
    is_externally_hosted: Optional[bool] = None
    raw_data: dict[str, Any] = None


# ============================================================================
# Search Result Data Classes
# ============================================================================

@dataclass(slots=True, frozen=True)
class SpotifySearchResult:
    """Represents a search result from Spotify."""
    
    type: str  # track, album, artist, show, episode
    id: str
    name: str
    uri: str
    external_urls: dict[str, str]
    
    # Track/Album specific
    artists: Optional[list[dict[str, str]]] = None
    album: Optional[dict[str, str]] = None
    
    # Show/Episode specific
    publisher: Optional[str] = None
    description: Optional[str] = None
    
    # Common
    images: Optional[list[dict[str, Any]]] = None
    release_date: Optional[str] = None


# ============================================================================
# Exceptions
# ============================================================================

class SpotifyAPIError(Exception):
    """Raised when Spotify API request fails."""
    
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Spotify API error {status_code}: {message}")


class SpotifyAuthError(Exception):
    """Raised when Spotify authentication fails."""
    pass


# ============================================================================
# Spotify API Client
# ============================================================================

class SpotifyClient:
    """Client for Spotify Web API.
    
    Uses Client Credentials Flow for backend-to-backend authentication.
    Documentation: https://developer.spotify.com/documentation/web-api
    """
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self, client_id: str, client_secret: str) -> None:
        """Initialize Spotify client.
        
        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._client = httpx.AsyncClient(timeout=30.0)
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def _authenticate(self) -> None:
        """Authenticate with Spotify using Client Credentials Flow."""
        # Encode client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data = {"grant_type": "client_credentials"}
        
        try:
            response = await self._client.post(self.AUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            
            auth_data = response.json()
            self._access_token = auth_data["access_token"]
            expires_in = auth_data["expires_in"]  # seconds
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("Successfully authenticated with Spotify API")
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            error_message = error_data.get("error_description", str(e))
            raise SpotifyAuthError(f"Authentication failed: {error_message}") from e
    
    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if not self._access_token or not self._token_expires_at:
            await self._authenticate()
        elif datetime.now() >= self._token_expires_at:
            logger.info("Access token expired, re-authenticating")
            await self._authenticate()
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
    
    async def _request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make an authenticated request to the Spotify API."""
        await self._ensure_authenticated()
        
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self._client.request(
                method, url, headers=headers, params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            error_message = error_data.get("error", {}).get("message", str(e))
            raise SpotifyAPIError(e.response.status_code, error_message) from e
        except httpx.RequestError as e:
            raise SpotifyAPIError(0, f"Request failed: {str(e)}") from e
    
    # ========================================================================
    # Search Methods
    # ========================================================================
    
    async def search(
        self,
        query: str,
        types: list[str],
        *,
        market: str = "US",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, list[SpotifySearchResult]]:
        """Search for tracks, albums, artists, shows, or episodes.
        
        Args:
            query: Search query
            types: List of item types to search for (track, album, artist, show, episode)
            market: ISO 3166-1 alpha-2 country code
            limit: Maximum number of results per type (1-50)
            offset: Index of first result to return
            
        Returns:
            Dictionary with keys for each type containing search results
        """
        params = {
            "q": query,
            "type": ",".join(types),
            "market": market,
            "limit": min(limit, 50),
            "offset": offset,
        }
        
        data = await self._request("GET", "search", params)
        
        results = {}
        for search_type in types:
            key = f"{search_type}s"
            if key in data:
                items = data[key].get("items", [])
                results[search_type] = [
                    SpotifySearchResult(
                        type=search_type,
                        id=item["id"],
                        name=item["name"],
                        uri=item["uri"],
                        external_urls=item.get("external_urls", {}),
                        artists=item.get("artists"),
                        album=item.get("album"),
                        publisher=item.get("publisher"),
                        description=item.get("description"),
                        images=item.get("images"),
                        release_date=item.get("release_date"),
                    )
                    for item in items
                ]
        
        return results
    
    # ========================================================================
    # Track Methods
    # ========================================================================
    
    async def get_track(self, track_id: str, *, market: str = "US") -> SpotifyTrack:
        """Get detailed information about a track.
        
        Args:
            track_id: Spotify track ID
            market: ISO 3166-1 alpha-2 country code
            
        Returns:
            Detailed track information
        """
        params = {"market": market}
        data = await self._request("GET", f"tracks/{track_id}", params)
        
        return SpotifyTrack(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            duration_ms=data["duration_ms"],
            explicit=data["explicit"],
            external_urls=data["external_urls"],
            external_ids=data.get("external_ids", {}),
            preview_url=data.get("preview_url"),
            track_number=data["track_number"],
            disc_number=data["disc_number"],
            popularity=data["popularity"],
            artists=data["artists"],
            album=data["album"],
            available_markets=data.get("available_markets", []),
            is_local=data.get("is_local", False),
            raw_data=data,
        )
    
    async def get_audio_features(self, track_id: str) -> SpotifyAudioFeatures:
        """Get audio features for a track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Audio analysis features
        """
        data = await self._request("GET", f"audio-features/{track_id}")
        
        return SpotifyAudioFeatures(
            id=data["id"],
            acousticness=data["acousticness"],
            danceability=data["danceability"],
            energy=data["energy"],
            instrumentalness=data["instrumentalness"],
            key=data["key"],
            liveness=data["liveness"],
            loudness=data["loudness"],
            mode=data["mode"],
            speechiness=data["speechiness"],
            tempo=data["tempo"],
            time_signature=data["time_signature"],
            valence=data["valence"],
            duration_ms=data["duration_ms"],
        )
    
    async def get_artist(self, artist_id: str) -> SpotifyArtist:
        """Get detailed information about an artist.
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            Detailed artist information
        """
        data = await self._request("GET", f"artists/{artist_id}")
        
        return SpotifyArtist(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            external_urls=data["external_urls"],
            genres=data.get("genres", []),
            popularity=data.get("popularity"),
            followers=data.get("followers", {}).get("total"),
            images=data.get("images"),
        )
    
    async def get_album(self, album_id: str, *, market: str = "US") -> SpotifyAlbum:
        """Get detailed information about an album.
        
        Args:
            album_id: Spotify album ID
            market: ISO 3166-1 alpha-2 country code
            
        Returns:
            Detailed album information
        """
        params = {"market": market}
        data = await self._request("GET", f"albums/{album_id}", params)
        
        return SpotifyAlbum(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            album_type=data["album_type"],
            release_date=data["release_date"],
            release_date_precision=data["release_date_precision"],
            total_tracks=data["total_tracks"],
            external_urls=data["external_urls"],
            images=data["images"],
            artists=data["artists"],
            genres=data.get("genres"),
            label=data.get("label"),
            popularity=data.get("popularity"),
            copyrights=data.get("copyrights"),
        )
    
    # ========================================================================
    # Podcast Methods
    # ========================================================================
    
    async def get_show(self, show_id: str, *, market: str = "US") -> SpotifyShow:
        """Get detailed information about a podcast show.
        
        Args:
            show_id: Spotify show ID
            market: ISO 3166-1 alpha-2 country code
            
        Returns:
            Detailed show information
        """
        params = {"market": market}
        data = await self._request("GET", f"shows/{show_id}", params)
        
        return SpotifyShow(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            description=data["description"],
            publisher=data["publisher"],
            external_urls=data["external_urls"],
            images=data["images"],
            languages=data["languages"],
            media_type=data["media_type"],
            explicit=data["explicit"],
            total_episodes=data["total_episodes"],
            copyrights=data.get("copyrights"),
            html_description=data.get("html_description"),
            is_externally_hosted=data.get("is_externally_hosted"),
            raw_data=data,
        )
    
    async def get_episode(self, episode_id: str, *, market: str = "US") -> SpotifyEpisode:
        """Get detailed information about a podcast episode.
        
        Args:
            episode_id: Spotify episode ID
            market: ISO 3166-1 alpha-2 country code
            
        Returns:
            Detailed episode information
        """
        params = {"market": market}
        data = await self._request("GET", f"episodes/{episode_id}", params)
        
        return SpotifyEpisode(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            description=data["description"],
            duration_ms=data["duration_ms"],
            explicit=data["explicit"],
            external_urls=data["external_urls"],
            images=data["images"],
            release_date=data["release_date"],
            release_date_precision=data["release_date_precision"],
            languages=data["languages"],
            audio_preview_url=data.get("audio_preview_url"),
            html_description=data.get("html_description"),
            show=data["show"],
            is_externally_hosted=data.get("is_externally_hosted"),
            raw_data=data,
        )
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self) -> SpotifyClient:
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()


def get_spotify_client(client_id: str, client_secret: str) -> SpotifyClient:
    """Factory function to create a Spotify client instance.
    
    Args:
        client_id: Spotify application client ID
        client_secret: Spotify application client secret
        
    Returns:
        Configured Spotify client
    """
    return SpotifyClient(client_id=client_id, client_secret=client_secret)
