from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseMedia

class MovieMedia(BaseMedia):
    """Complete movie metadata from enrichment."""

    # Basic Info
    title: str = Field(..., description="Movie title")
    tagline: Optional[str] = Field(None, description="Movie tagline")
    overview: Optional[str] = Field(None, description="Plot synopsis")
    
    # Release Info
    release_date: Optional[datetime] = Field(None, description="Release date")
    year: Optional[int] = Field(None, description="Release year")
    
    # Runtime & Production
    runtime_min: Optional[int] = Field(None, description="Runtime in minutes")

    # Categories
    genres: Optional[list[str]] = Field(None, description="List of genre names")
    languages: Optional[list[str]] = Field(None, description="List of spoken languages")

    # Ratings
    vote_average: Optional[float] = Field(None, description="Average rating (0-10)")
    vote_count: Optional[int] = Field(None, description="Number of votes")
    
    # People
    cast: Optional[list[str]] = Field(None, description="Top cast members")
    
    # Flags
    rating: Optional[str] = Field(None, description="Adult content flag")
    
