"""Pydantic schemas for enriched metadata from external APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class CastMember(BaseModel):
    """A cast member in a movie."""
    
    name: str = Field(..., description="Actor's name")
    character: str = Field(..., description="Character name")
    order: int = Field(..., description="Billing order (0 = top billed)")
    profile_path: Optional[str] = Field(None, description="Profile image path")


class CrewMember(BaseModel):
    """A crew member in a movie."""
    
    name: str = Field(..., description="Crew member's name")
    job: str = Field(..., description="Job title (Director, Writer, etc.)")
    department: str = Field(..., description="Department (Directing, Writing, etc.)")


class ImageMetadata(BaseModel):
    """Image metadata from TMDb."""
    
    file_path: str = Field(..., description="Image file path")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    aspect_ratio: Optional[float] = Field(None, description="Image aspect ratio")
    vote_average: Optional[float] = Field(None, description="Community rating")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    iso_639_1: Optional[str] = Field(None, description="Language code")


class MovieMetadata(BaseModel):
    """Complete movie metadata from enrichment."""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb movie ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    
    # Basic Info
    title: str = Field(..., description="Movie title")
    original_title: Optional[str] = Field(None, description="Original title in native language")
    tagline: Optional[str] = Field(None, description="Movie tagline")
    overview: Optional[str] = Field(None, description="Plot synopsis")
    
    # Release Info
    release_date: Optional[datetime] = Field(None, description="Release date")
    year: Optional[int] = Field(None, description="Release year")
    status: Optional[str] = Field(None, description="Release status (Released, In Production, etc.)")
    
    # Runtime & Production
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")
    budget: Optional[int] = Field(None, description="Production budget in USD")
    revenue: Optional[int] = Field(None, description="Box office revenue in USD")
    
    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genre names")
    languages: Optional[list[str]] = Field(None, description="List of spoken languages")
    countries: Optional[list[str]] = Field(None, description="List of production countries")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    popularity: Optional[float] = Field(None, description="Popularity score")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Top cast members")
    crew: Optional[list[CrewMember]] = Field(None, description="Key crew members")
    
    # Images
    poster_path: Optional[str] = Field(None, description="Primary poster image path")
    backdrop_path: Optional[str] = Field(None, description="Primary backdrop image path")
    posters: Optional[list[ImageMetadata]] = Field(None, description="Additional posters")
    backdrops: Optional[list[ImageMetadata]] = Field(None, description="Additional backdrops")
    
    # URLs
    poster_url: Optional[str] = Field(None, description="Full poster URL")
    backdrop_url: Optional[str] = Field(None, description="Full backdrop URL")
    homepage: Optional[str] = Field(None, description="Official website")
    
    # Flags
    adult: Optional[bool] = Field(None, description="Adult content flag")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tmdb_id": 603,
                "imdb_id": "tt0133093",
                "title": "The Matrix",
                "original_title": "The Matrix",
                "tagline": "Welcome to the Real World.",
                "overview": "Set in the 22nd century, The Matrix tells the story of a computer hacker...",
                "release_date": "1999-03-31T00:00:00",
                "year": 1999,
                "runtime_min": 136,
                "genres": ["Action", "Science Fiction"],
                "vote_average": 8.2,
                "vote_count": 23000,
                "cast": [
                    {
                        "name": "Keanu Reeves",
                        "character": "Neo",
                        "order": 0,
                    }
                ],
            }
        }



class TvShowMetadata(BaseModel):
    """Entire TV show metadata from enrichment. (not one episode)"""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb TV show ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    tvmaze_id: Optional[int] = Field(None, description="TVmaze identifier")
    
    # Basic Info
    name: str = Field(..., description="TV show name")
    original_name: Optional[str] = Field(None, description="Original name in native language")
    tagline: Optional[str] = Field(None, description="Show tagline")
    overview: Optional[str] = Field(None, description="Show synopsis")
    type: Optional[str] = Field(None, description="Show type (Scripted, Reality, etc.)")
    status: Optional[str] = Field(None, description="Show status (Returning, Ended, etc.)")
    
    # Air Dates
    first_air_date: Optional[datetime] = Field(None, description="First episode air date")
    last_air_date: Optional[datetime] = Field(None, description="Last episode air date")
    
    # Episodes & Seasons
    number_of_seasons: Optional[int] = Field(None, description="Total number of seasons")
    number_of_episodes: Optional[int] = Field(None, description="Total number of episodes")
    
    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genre names")
    languages: Optional[list[str]] = Field(None, description="List of spoken languages")
    countries: Optional[list[str]] = Field(None, description="List of origin countries")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    popularity: Optional[float] = Field(None, description="Popularity score")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Main cast members")
    crew: Optional[list[CrewMember]] = Field(None, description="Key crew members")
    created_by: Optional[list[str]] = Field(None, description="Show creators")
    
    # Images
    poster_path: Optional[str] = Field(None, description="Primary poster image path")
    backdrop_path: Optional[str] = Field(None, description="Primary backdrop image path")
    posters: Optional[list[ImageMetadata]] = Field(None, description="Additional posters")
    backdrops: Optional[list[ImageMetadata]] = Field(None, description="Additional backdrops")
    
    # URLs
    poster_url: Optional[str] = Field(None, description="Full poster URL")
    backdrop_url: Optional[str] = Field(None, description="Full backdrop URL")
    homepage: Optional[str] = Field(None, description="Official website")
    
    # Networks
    networks: Optional[list[str]] = Field(None, description="Broadcasting networks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tmdb_id": 1396,
                "imdb_id": "tt0903747",
                "name": "Breaking Bad",
                "original_name": "Breaking Bad",
                "overview": "A high school chemistry teacher diagnosed with cancer...",
                "first_air_date": "2008-01-20T00:00:00",
                "number_of_seasons": 5,
                "number_of_episodes": 62,
                "genres": ["Drama", "Crime", "Thriller"],
                "vote_average": 9.0,
                "vote_count": 12000,
                "status": "Ended",
            }
        }


class TvEpisodeMetadata(BaseModel):
    """TV episode metadata from enrichment."""
    
    # IDs
    tmdb_id: Optional[int] = Field(None, description="TMDb episode ID")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    tvmaze_id: Optional[int] = Field(None, description="TVmaze identifier")
    
    # Series Info
    series_name: Optional[str] = Field(None, description="TV show name")
    series_tmdb_id: Optional[int] = Field(None, description="TMDb TV show ID")
    
    # Basic Info
    name: str = Field(..., description="Episode name")
    overview: Optional[str] = Field(None, description="Episode synopsis")
    
    # Episode Info
    season_number: int = Field(..., description="Season number")
    episode_number: int = Field(..., description="Episode number within season")
    air_date: Optional[datetime] = Field(None, description="Air date")
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")
    
    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    
    # People
    cast: Optional[list[CastMember]] = Field(None, description="Episode guest cast")
    crew: Optional[list[CrewMember]] = Field(None, description="Episode crew (director, writer)")
    
    # Images
    still_path: Optional[str] = Field(None, description="Episode still image path")
    still_url: Optional[str] = Field(None, description="Full still image URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tmdb_id": 62085,
                "series_name": "Breaking Bad",
                "name": "Pilot",
                "season_number": 1,
                "episode_number": 1,
                "air_date": "2008-01-20T00:00:00",
                "runtime_min": 58,
                "vote_average": 8.2,
            }
        }



class MusicTrackMetadata(BaseModel):
    """Music track metadata from enrichment (placeholder for future)."""
    
    # IDs
    musicbrainz_id: Optional[str] = Field(None, description="MusicBrainz recording ID")
    isrc: Optional[str] = Field(None, description="International Standard Recording Code")
    
    # Basic Info
    title: str = Field(..., description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album title")
    
    # Track Info
    track_number: Optional[int] = Field(None, description="Track number on album")
    disc_number: Optional[int] = Field(None, description="Disc number")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    year: Optional[int] = Field(None, description="Release year")
    
    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genres")



class PodcastEpisodeMetadata(BaseModel):
    """Podcast episode metadata from enrichment (placeholder for future)."""
    
    # IDs
    guid: Optional[str] = Field(None, description="Episode GUID")
    
    # Basic Info
    title: str = Field(..., description="Episode title")
    show_name: Optional[str] = Field(None, description="Podcast show name")
    description: Optional[str] = Field(None, description="Episode description")
    
    # Episode Info
    pub_date: Optional[datetime] = Field(None, description="Publication date")
    duration_s: Optional[int] = Field(None, description="Duration in seconds")
    
    # Images
    image_url: Optional[str] = Field(None, description="Episode artwork URL")



class EnrichedMetadata(BaseModel):
    """Container for any type of enriched metadata."""
    
    movie: Optional[MovieMetadata] = Field(None, description="Movie metadata if media type is movie")
    tv_show: Optional[TvShowMetadata] = Field(None, description="TV show metadata if media type is tv")
    tv_episode: Optional[TvEpisodeMetadata] = Field(None, description="TV episode metadata if media type is tv")
    music: Optional[MusicTrackMetadata] = Field(None, description="Music metadata if media type is music")
    podcast: Optional[PodcastEpisodeMetadata] = Field(None, description="Podcast metadata if media type is podcast")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie": {
                    "tmdb_id": 603,
                    "title": "The Matrix",
                    "year": 1999,
                    "genres": ["Action", "Science Fiction"],
                }
            }
        }
