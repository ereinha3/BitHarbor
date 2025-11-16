"""Database models for BitHarbor.

This module exports all SQLAlchemy models for the application.
Each model corresponds to a Pydantic schema in the domain package.
"""

from __future__ import annotations

# Auth models
from .auth import Admin, Participant, AdminParticipantLink

# Media models
from .ann import IdMap
from .movie import Movie
from .tv import TvShow, TvSeason, TvEpisode
from .music import MusicArtist, MusicAlbum, MusicTrack
from .podcast import PodcastShow, PodcastEpisode
from .personal import PersonalMedia
from .video import Video

__all__ = [
    # Auth
    "Admin",
    "Participant",
    "AdminParticipantLink",
    # ANN
    "IdMap",
    # Movies
    "Movie",
    # TV
    "TvShow",
    "TvSeason",
    "TvEpisode",
    # Music
    "MusicArtist",
    "MusicAlbum",
    "MusicTrack",
    # Podcasts
    "PodcastShow",
    "PodcastEpisode",
    # Personal
    "PersonalMedia",
    # Videos
    "Video",
]
