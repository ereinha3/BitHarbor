from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class MediaType(str, Enum):
    MOVIE = "movie"
    TV = "tv"
    MUSIC = "music"
    PODCAST = "podcast"
    VIDEO = "video"
    PERSONAL = "personal"


class SourceType(str, Enum):
    CATALOG = "catalog"
    HOME = "home"


class EmbeddingSource(str, Enum):
    TEXT = "text"
    CONTENT = "content"
    TEXT_IMAGE = "text+image"


class FilePath(Base):
    __tablename__ = "file_paths"

    hdd_path_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    modality: Mapped[str] = mapped_column(String(16), nullable=False)
    abs_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    media_items: Mapped[list["MediaCore"]] = relationship(
        back_populates="file_path",
        cascade="all, delete-orphan",
    )


class MediaCore(Base):
    __tablename__ = "media_core"
    __table_args__ = (
        Index("idx_media_core_filehash", "file_hash"),
        Index("idx_media_core_vectorhash", "vector_hash"),
    )

    media_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    embedding_source: Mapped[str] = mapped_column(String(16), nullable=False)
    date_original: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    hdd_path_id: Mapped[int] = mapped_column(
        ForeignKey("file_paths.hdd_path_id", ondelete="CASCADE"), nullable=False
    )
    preview_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    file_path: Mapped[FilePath] = relationship(back_populates="media_items")
    movie: Mapped[Optional["Movie"]] = relationship(back_populates="core", uselist=False)
    tv_episode: Mapped[Optional["TvEpisode"]] = relationship(back_populates="core", uselist=False)
    music_track: Mapped[Optional["MusicTrack"]] = relationship(back_populates="core", uselist=False)
    podcast_episode: Mapped[Optional["PodcastEpisode"]] = relationship(
        back_populates="core", uselist=False
    )
    online_video: Mapped[Optional["OnlineVideo"]] = relationship(
        back_populates="core", uselist=False
    )
    personal_media: Mapped[Optional["PersonalMedia"]] = relationship(
        back_populates="core", uselist=False
    )


class IdMap(Base):
    __tablename__ = "idmap"

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vector_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), nullable=False
    )

    media: Mapped[MediaCore] = relationship()


class Movie(Base):
    __tablename__ = "movies"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(32))
    original_title: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    runtime_min: Mapped[Optional[int]] = mapped_column(Integer)
    genres: Mapped[Optional[str]] = mapped_column(Text)
    languages: Mapped[Optional[str]] = mapped_column(Text)
    countries: Mapped[Optional[str]] = mapped_column(Text)
    overview: Mapped[Optional[str]] = mapped_column(Text)
    tagline: Mapped[Optional[str]] = mapped_column(Text)
    cast_json: Mapped[Optional[str]] = mapped_column(Text)
    crew_json: Mapped[Optional[str]] = mapped_column(Text)
    posters_json: Mapped[Optional[str]] = mapped_column(Text)
    backdrops_json: Mapped[Optional[str]] = mapped_column(Text)
    providers_json: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    core: Mapped[MediaCore] = relationship(back_populates="movie")

    __table_args__ = (
        Index("idx_movies_tmdb", "tmdb_id"),
        Index("idx_movies_imdb", "imdb_id"),
    )


class TvSeries(Base):
    __tablename__ = "tv_series"

    series_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer)
    tvmaze_id: Mapped[Optional[int]] = mapped_column(Integer)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(32))
    name: Mapped[Optional[str]] = mapped_column(Text)
    original_name: Mapped[Optional[str]] = mapped_column(Text)
    first_air_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_air_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    genres: Mapped[Optional[str]] = mapped_column(Text)
    overview: Mapped[Optional[str]] = mapped_column(Text)
    cast_json: Mapped[Optional[str]] = mapped_column(Text)
    crew_json: Mapped[Optional[str]] = mapped_column(Text)
    posters_json: Mapped[Optional[str]] = mapped_column(Text)
    backdrops_json: Mapped[Optional[str]] = mapped_column(Text)
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))

    seasons: Mapped[list["TvSeason"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )
    episodes: Mapped[list["TvEpisode"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class TvSeason(Base):
    __tablename__ = "tv_season"

    season_media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    series_id: Mapped[str] = mapped_column(
        ForeignKey("tv_series.series_id", ondelete="CASCADE"), nullable=False
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    air_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    poster_json: Mapped[Optional[str]] = mapped_column(Text)
    episodes_count: Mapped[Optional[int]] = mapped_column(Integer)

    series: Mapped[TvSeries] = relationship(back_populates="seasons")


class TvEpisode(Base):
    __tablename__ = "tv_episode"
    __table_args__ = (
        Index("idx_tv_episode_series_season_ep", "series_id", "season_number", "episode_number"),
    )

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    series_id: Mapped[str] = mapped_column(
        ForeignKey("tv_series.series_id", ondelete="CASCADE"), nullable=False
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer)
    tvmaze_id: Mapped[Optional[int]] = mapped_column(Integer)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(32))
    name: Mapped[Optional[str]] = mapped_column(Text)
    air_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    runtime_min: Mapped[Optional[int]] = mapped_column(Integer)
    overview: Mapped[Optional[str]] = mapped_column(Text)
    stills_json: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    series: Mapped[TvSeries] = relationship(back_populates="episodes")
    core: Mapped[MediaCore] = relationship(back_populates="tv_episode")


class MusicTrack(Base):
    __tablename__ = "music_track"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    musicbrainz_recording_id: Mapped[Optional[str]] = mapped_column(String(64))
    isrc: Mapped[Optional[str]] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(Text)
    artist_name: Mapped[Optional[str]] = mapped_column(Text)
    artist_mb_id: Mapped[Optional[str]] = mapped_column(String(64))
    album_title: Mapped[Optional[str]] = mapped_column(Text)
    album_mb_id: Mapped[Optional[str]] = mapped_column(String(64))
    track_number: Mapped[Optional[int]] = mapped_column(Integer)
    disc_number: Mapped[Optional[int]] = mapped_column(Integer)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    genres: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    lyrics: Mapped[Optional[str]] = mapped_column(Text)
    art_json: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    core: Mapped[MediaCore] = relationship(back_populates="music_track")


class MusicAlbum(Base):
    __tablename__ = "music_album"

    album_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    album_mb_id: Mapped[Optional[str]] = mapped_column(String(64))
    title: Mapped[Optional[str]] = mapped_column(Text)
    artist_name: Mapped[Optional[str]] = mapped_column(Text)
    artist_mb_id: Mapped[Optional[str]] = mapped_column(String(64))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    genres: Mapped[Optional[str]] = mapped_column(Text)
    art_json: Mapped[Optional[str]] = mapped_column(Text)
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)


class MusicArtist(Base):
    __tablename__ = "music_artist"

    artist_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    artist_mb_id: Mapped[Optional[str]] = mapped_column(String(64))
    name: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)


class PodcastShow(Base):
    __tablename__ = "podcast_show"

    show_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    podcastindex_id: Mapped[Optional[int]] = mapped_column(Integer)
    rss_url: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    categories: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(16))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    episodes: Mapped[list["PodcastEpisode"]] = relationship(
        back_populates="show", cascade="all, delete-orphan"
    )


class PodcastEpisode(Base):
    __tablename__ = "podcast_episode"
    __table_args__ = (
        Index("idx_podcast_episode_show_date", "show_id", "pub_date"),
    )

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    show_id: Mapped[str] = mapped_column(
        ForeignKey("podcast_show.show_id", ondelete="CASCADE"), nullable=False
    )
    guid: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    pub_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    enclosure_url: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    core: Mapped[MediaCore] = relationship(back_populates="podcast_episode")
    show: Mapped[PodcastShow] = relationship(back_populates="episodes")


class OnlineVideo(Base):
    __tablename__ = "online_video"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[Optional[str]] = mapped_column(String(32))
    platform_id: Mapped[Optional[str]] = mapped_column(String(64))
    channel_name: Mapped[Optional[str]] = mapped_column(Text)
    uploader: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thumb_url: Mapped[Optional[str]] = mapped_column(Text)
    meta_fingerprint: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_raw: Mapped[Optional[str]] = mapped_column(Text)
    metadata_enriched: Mapped[Optional[str]] = mapped_column(Text)

    core: Mapped[MediaCore] = relationship(back_populates="online_video")

    __table_args__ = (
        Index("idx_online_video_platform_id", "platform", "platform_id"),
    )


class PersonalMedia(Base):
    __tablename__ = "personal_media"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_core.media_id", ondelete="CASCADE"), primary_key=True
    )
    device_make: Mapped[Optional[str]] = mapped_column(Text)
    device_model: Mapped[Optional[str]] = mapped_column(Text)
    capture_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    gps_lat: Mapped[Optional[float]] = mapped_column(Float)
    gps_lon: Mapped[Optional[float]] = mapped_column(Float)
    orientation: Mapped[Optional[str]] = mapped_column(String(16))
    persons_json: Mapped[Optional[str]] = mapped_column(Text)
    album_name: Mapped[Optional[str]] = mapped_column(Text)
    sidecar_json: Mapped[Optional[str]] = mapped_column(Text)

    core: Mapped[MediaCore] = relationship(back_populates="personal_media")


class Admin(Base):
    __tablename__ = "admins"

    admin_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    participants: Mapped[list["AdminParticipantLink"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    participant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    handle: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    preferences_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    admins: Mapped[list["AdminParticipantLink"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )


class AdminParticipantLink(Base):
    __tablename__ = "admin_participants"
    __table_args__ = (
        UniqueConstraint("admin_id", "participant_id", name="uq_admin_participant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[str] = mapped_column(
        ForeignKey("admins.admin_id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.participant_id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), default="viewer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    admin: Mapped[Admin] = relationship(back_populates="participants")
    participant: Mapped[Participant] = relationship(back_populates="admins")

