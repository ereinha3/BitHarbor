from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from domain.media.movies import MovieMedia

MediaTypeLiteral = Literal["movie", "tv", "music", "podcast", "personal", "video"]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    types: Optional[list[MediaTypeLiteral]] = None
    k: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    media_id: str
    score: float
    type: MediaTypeLiteral
    title: Optional[str] = None
    preview_url: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]


class LocalMovieSearchHit(BaseModel):
    movie_id: int = Field(..., description="Database identifier for the movie")
    score: float = Field(..., description="Similarity score (cosine, 1.0 is best)")
    media_id: str = Field(..., description="Identifier stored in the ANN map")
    movie: MovieMedia


class LocalMovieSearchResponse(BaseModel):
    results: list[LocalMovieSearchHit] = Field(default_factory=list)

