"""Schemas for catalog acquisition endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .media.movies import MovieMedia


class InternetArchiveIngestRequest(BaseModel):
    """Request to download and ingest a movie from Internet Archive."""

    identifier: str = Field(
        ...,
        min_length=1,
        description="Internet Archive item identifier (e.g., 'fantastic-planet__1973')",
        examples=["fantastic-planet__1973", "night_of_the_living_dead"],
    )
    title: Optional[str] = Field(
        default=None,
        description="Movie title from search (used for TMDb matching)",
    )
    year: Optional[int] = Field(
        default=None,
        description="Release year from search (used for TMDb matching)",
    )
    download_dir: Optional[str] = Field(
        default=None,
        description="Directory for temporary downloads (default: /tmp/bitharbor-downloads)",
        examples=["/tmp/downloads", "/mnt/temp"],
    )
    source_type: str = Field(
        default="catalog",
        description="Media source type",
        pattern="^(catalog|home)$",
    )
    cleanup_after_ingest: bool = Field(
        default=True,
        description="Delete downloaded files after successful ingestion",
    )
    include_subtitles: bool = Field(
        default=True,
        description="Download subtitle files (SRT, VTT) if available",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "fantastic-planet__1973",
                "title": "Fantastic Planet",
                "year": 1973,
                "download_dir": "/tmp/bitharbor-downloads",
                "source_type": "catalog",
                "cleanup_after_ingest": True,
                "include_subtitles": True,
            }
        }


class CatalogSearchRequest(BaseModel):
    """Request to search Internet Archive catalog."""

    query: str = Field(
        ...,
        min_length=1,
        description="Search query (movie title)",
        examples=["Metropolis", "Night of the Living Dead", "Nosferatu"],
    )
    rows: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    sorts: Optional[list[str]] = Field(
        default=None,
        description="Sort criteria (e.g., ['downloads desc', 'year desc'])",
        examples=[["downloads desc"], ["year asc"]],
    )
    filters: Optional[list[str]] = Field(
        default=None,
        description="Additional Lucene filter clauses (e.g., ['language:eng', 'year:1970'])",
        examples=[["language:eng"], ["year:[1950 TO 1980]"]],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Metropolis",
                "rows": 10,
                "sorts": ["downloads desc"],
                "filters": ["language:eng"],
            }
        }


class CatalogSearchResult(BaseModel):
    """Single search result from Internet Archive catalog."""

    identifier: str = Field(..., description="Internet Archive item identifier")
    title: Optional[str] = Field(None, description="Movie title")
    year: Optional[str] = Field(None, description="Release year")
    description: Optional[str] = Field(None, description="Movie description")
    downloads: Optional[int] = Field(None, description="Number of downloads")
    item_size: Optional[int] = Field(None, description="Total size in bytes")
    avg_rating: Optional[float] = Field(None, description="Average user rating (0-5)")
    num_reviews: Optional[int] = Field(None, description="Number of user reviews")

    @property
    def score(self) -> float:
        """Calculate a ranking score based on downloads and rating.

        Higher downloads and ratings result in higher scores.
        This helps prioritize the best version when there are duplicates.
        """

        download_score = (self.downloads or 0) / 10000  # Normalize downloads
        rating_score = (self.avg_rating or 0) * 2  # Rating out of 10
        return download_score + rating_score


class CatalogSearchResponse(BaseModel):
    """Response from catalog search."""

    results: list[CatalogSearchResult] = Field(default_factory=list)
    total: int = Field(..., description="Total number of results found")


class CatalogMatchCandidate(BaseModel):
    """Single Internet Archive candidate matched to TMDb metadata."""

    identifier: str = Field(..., description="Internet Archive identifier")
    score: float = Field(..., ge=0.0, le=1.0)
    downloads: Optional[int] = Field(None, description="Number of downloads")
    movie: MovieMedia


class CatalogMatch(BaseModel):
    """TMDb movie matched to its best Internet Archive candidate."""

    match_key: str = Field(..., description="Key used to retrieve the stored match")
    tmdb_id: int = Field(..., description="TMDb movie identifier")
    tmdb_movie: MovieMedia
    best_candidate: CatalogMatchCandidate
    candidates: list[CatalogMatchCandidate] = Field(default_factory=list)


class CatalogMatchResponse(BaseModel):
    """Response containing deduplicated catalog matches."""

    matches: list[CatalogMatch] = Field(default_factory=list)
    total: int = Field(..., description="Total number of matched items")


class CatalogDownloadRequest(BaseModel):
    """Request to plan or execute a catalog-backed download."""

    match_key: str = Field(..., description="Match key obtained from catalog search")
    destination: Optional[str] = Field(
        default=None,
        description="Override destination directory for downloads"
    )
    execute: bool = Field(
        default=False,
        description="If true, perform the download; otherwise return plan information"
    )


class CatalogDownloadResponse(BaseModel):
    """Response returned for planned or executed downloads."""

    match_key: str
    identifier: str
    title: Optional[str]
    destination: Optional[str]
    video_file: Optional[str]
    metadata_xml_file: Optional[str]
    cover_art_file: Optional[str]
    subtitle_files: list[str] = Field(default_factory=list)
    downloaded: bool = Field(default=False)
    video_path: Optional[str] = None
    subtitle_paths: list[str] = Field(default_factory=list)
    file_hash: Optional[str] = None
    vector_hash: Optional[str] = None
    vector_row_id: Optional[int] = None
    movie_id: Optional[int] = None
    created: Optional[bool] = None
