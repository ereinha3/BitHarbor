from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .ingest import MediaTypeLiteral


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

