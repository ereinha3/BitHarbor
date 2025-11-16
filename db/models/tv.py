from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class TvShow(Base):
    """TV show with complete metadata."""
    
    __tablename__ = "tv_shows"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="tv", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    catalog_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    catalog_downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Air Dates
    first_air_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_air_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Episodes & Seasons
    number_of_seasons: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    number_of_episodes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Categories (stored as JSON arrays)
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    languages: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Ratings
    vote_average: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vote_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # People (stored as JSON arrays)
    cast: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    seasons: Mapped[list["TvSeason"]] = relationship(
        "TvSeason",
        back_populates="show",
        cascade="all, delete-orphan"
    )


class TvSeason(Base):
    """TV season metadata."""
    
    __tablename__ = "tv_seasons"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    show_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tv_shows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="tv", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    show: Mapped["TvShow"] = relationship("TvShow", back_populates="seasons")
    episodes: Mapped[list["TvEpisode"]] = relationship(
        "TvEpisode",
        back_populates="season",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_season_show_number', 'show_id', 'season_number'),
    )
    


class TvEpisode(Base):
    """TV episode metadata."""
    
    __tablename__ = "tv_episodes"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    season_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tv_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="tv", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    air_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    runtime_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    season: Mapped["TvSeason"] = relationship("TvSeason", back_populates="episodes")
    
    __table_args__ = (
        Index('idx_episode_season_number', 'season_id', 'episode_number'),
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
