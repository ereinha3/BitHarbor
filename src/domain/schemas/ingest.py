from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


MediaTypeLiteral = Literal["movie", "tv", "music", "podcast", "video", "personal"]
SourceTypeLiteral = Literal["catalog", "home"]


class IngestRequest(BaseModel):
    path: str
    media_type: MediaTypeLiteral = "personal"
    source_type: SourceTypeLiteral = "home"
    metadata: Optional[dict[str, Any]] = None
    poster_path: Optional[str] = None


class IngestResponse(BaseModel):
    media_id: str
    file_hash: str
    vector_hash: str

