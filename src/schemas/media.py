from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from bitharbor.schemas.ingest import MediaTypeLiteral, SourceTypeLiteral


class MediaSummary(BaseModel):
    media_id: str
    type: MediaTypeLiteral
    title: Optional[str] = None
    source_type: SourceTypeLiteral
    vector_hash: str


class MediaDetail(MediaSummary):
    file_hash: str
    metadata: Optional[dict[str, Any]] = None


class MediaListResponse(BaseModel):
    items: list[MediaSummary]
    total: int

