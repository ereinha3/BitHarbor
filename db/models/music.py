from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class MusicArtist(Base):
    """Music artist metadata."""
    
    __tablename__ = "music_artists"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="music", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    catalog_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    catalog_downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Basic Info
    artist: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    albums: Mapped[list["MusicAlbum"]] = relationship(
        "MusicAlbum",
        back_populates="artist",
        cascade="all, delete-orphan"
    )


class MusicAlbum(Base):
    """Music album metadata."""
    
    __tablename__ = "music_albums"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    artist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("music_artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="music", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Basic Info
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    release_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    artist: Mapped["MusicArtist"] = relationship("MusicArtist", back_populates="albums")
    tracks: Mapped[list["MusicTrack"]] = relationship(
        "MusicTrack",
        back_populates="album",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_album_artist_title', 'artist_id', 'title'),
    )
    


class MusicTrack(Base):
    """Music track metadata."""
    
    __tablename__ = "music_tracks"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    album_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("music_albums.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Hashes - embedding_hash is unique
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # File Info
    path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), default="music", nullable=False)
    
    # Catalog Info
    catalog_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Basic Info
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    track_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Images (stored as JSON)
    poster: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    backdrop: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    album: Mapped["MusicAlbum"] = relationship("MusicAlbum", back_populates="tracks")
    
    __table_args__ = (
        Index('idx_track_album_number', 'album_id', 'track_number'),
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
