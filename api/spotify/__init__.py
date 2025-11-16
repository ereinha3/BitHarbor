"""Spotify Web API client module for music and podcast enrichment.

API Documentation: https://developer.spotify.com/documentation/web-api
Authentication: Client Credentials Flow (for backend-to-backend)
"""

from api.spotify.client import (
    SpotifyClient,
    SpotifyTrack,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyAudioFeatures,
    SpotifyShow,
    SpotifyEpisode,
    SpotifySearchResult,
)

__all__ = [
    "SpotifyClient",
    "SpotifyTrack",
    "SpotifyAlbum",
    "SpotifyArtist",
    "SpotifyAudioFeatures",
    "SpotifyShow",
    "SpotifyEpisode",
    "SpotifySearchResult",
]
