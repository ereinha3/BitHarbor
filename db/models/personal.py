from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PersonalMedia(Base):
    """Personal media (user-uploaded content without catalog metadata)."""
    
    __tablename__ = "personal_media"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="personal", nullable=False)
    
    # Catalog Info (usually empty for personal media)
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    catalog_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    catalog_downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Basic Info
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    @classmethod
    async def get_all_hashes(cls, session) -> dict[str, list[str]]:
        """Get all hashes in the table."""
        from sqlalchemy import select
        result = await session.execute(
            select(cls.file_hash, cls.embedding_hash).where(
                cls.file_hash.isnot(None) | cls.embedding_hash.isnot(None)
            )
        )
        rows = result.all()
        return {
            "file_hashes": [row[0] for row in rows if row[0]],
            "embedding_hashes": [row[1] for row in rows if row[1]]
        }
    
    @classmethod
    async def hash_exists(cls, session, embedding_hash: str) -> bool:
        """Check if an embedding hash already exists in the table."""
        from sqlalchemy import select
        result = await session.execute(
            select(cls).where(cls.embedding_hash == embedding_hash)
        )
        return result.scalar_one_or_none() is not None
