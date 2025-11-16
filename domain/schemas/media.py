from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .enrichment import EnrichedMetadata
from .ingest import MediaTypeLiteral, SourceTypeLiteral


class MediaSummary(BaseModel):
    media_id: str
    type: MediaTypeLiteral
    title: Optional[str] = None
    source_type: SourceTypeLiteral
    vector_hash: str


class MediaDetail(MediaSummary):
    file_hash: str
    metadata: Optional[dict[str, Any]] = None
    enriched_metadata: Optional[EnrichedMetadata] = Field(
        None,
        description="Type-safe enriched metadata from external APIs (TMDb, etc.)",
    )


class MediaListResponse(BaseModel):
    items: list[MediaSummary]
    total: int

