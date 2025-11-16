from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

SourceTypeLiteral = Literal["catalog", "home"]

class ImageMetadata(BaseModel):
    """Image metadata from TMDb."""
    
    file_path: str = Field(..., description="Image file path")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    aspect_ratio: Optional[float] = Field(None, description="Image aspect ratio")

class BaseMedia(BaseModel):
    """Base media model."""

    file_hash: Optional[str] = Field(None, description="File hash")
    embedding_hash: Optional[str] = Field(None, description="Embedding hash")
    path: Optional[str] = Field(None, description="File path")
    format: Optional[str] = Field(None, description="File format/extension")
    media_type: Optional[str] = Field(None, description="Logical media type (movie, tv, etc.)")
    catalog_source: Optional[str] = Field(
        None, description="External catalog source (tmdb, internet_archive, etc.)"
    )
    catalog_id: Optional[str] = Field(None, description="Identifier within the external catalog")
    catalog_score: Optional[float] = Field(
        None, description="Ranking score provided by the catalog (popularity, downloads, etc.)"
    )
    catalog_downloads: Optional[int] = Field(
        None, description="Download count or similar metric from the catalog"
    )
    poster: Optional[ImageMetadata] = Field(None, description="Primary poster image path")
    backdrop: Optional[ImageMetadata] = Field(None, description="Primary backdrop image path")