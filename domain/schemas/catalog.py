"""Schemas for catalog acquisition endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class InternetArchiveIngestRequest(BaseModel):
    """Request to download and ingest a movie from Internet Archive."""

    identifier: str = Field(
        ...,
        min_length=1,
        description="Internet Archive item identifier (e.g., 'fantastic-planet__1973')",
        examples=["fantastic-planet__1973", "night_of_the_living_dead"],
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


class CatalogSearchResponse(BaseModel):
    """Response from catalog search."""

    results: list[CatalogSearchResult] = Field(default_factory=list)
    total: int = Field(..., description="Total number of results found")
