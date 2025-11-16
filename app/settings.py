from __future__ import annotations

import os
import secrets
from pathlib import Path
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()

_DEFAULT_DATA_ROOT = Path(
    os.getenv("BITHARBOR_DATA_ROOT")
    or os.getenv("RAID_PATH")
    or "/var/lib/bitharbor"
)
_DEFAULT_POOL_ROOT = Path(
    os.getenv("BITHARBOR_POOL_ROOT")
    or os.getenv("RAID_PATH")
    or "/mnt/pool"
)
_VECTOR_ROOT = Path(
    os.getenv("BITHARBOR_VECTOR_DB_PATH")
    or os.getenv("VECTOR_DB_PATH")
    or "/var/lib/bitharbor/index"
)
_DEFAULT_VECTORS_PATH = Path(
    os.getenv("BITHARBOR_ANN_VECTORS_PATH")
    or (_VECTOR_ROOT / "movies" / "vectors.fp32")
)
_DEFAULT_INDEX_DIRECTORY = Path(
    os.getenv("BITHARBOR_ANN_INDEX_DIRECTORY")
    or (_VECTOR_ROOT / "movies" / "diskann")
)


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False
    data_root: Path = _DEFAULT_DATA_ROOT
    pool_root: Path = _DEFAULT_POOL_ROOT
    log_level: str = "INFO"


class DatabaseSettings(BaseModel):
    url: str = "sqlite+aiosqlite:////var/lib/bitharbor/bitharbor.sqlite"
    echo: bool = False


class SecuritySettings(BaseModel):
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours


class EmbeddingSettings(BaseModel):
    model_name: Literal["imagebind_huge"] = "imagebind_huge"
    device: Literal["cuda", "cpu", "auto"] = "auto"
    dim: int = 1024
    video_frames: int = 8
    fuse_poster_weight: float = 0.2
    round_eps: float = 1e-6


class AnnSettings(BaseModel):
    backend: Literal["diskann"] = "diskann"
    metric: Literal["cosine", "l2", "mips"] = "cosine"
    enabled: bool = False
    graph_degree: int = 64
    complexity: int = 100
    search_memory_budget: float = 2.0  # GB
    num_threads: int = 0  # 0 == auto
    rebuild_batch: int = 1
    vectors_path: Path = _DEFAULT_VECTORS_PATH
    index_directory: Path = _DEFAULT_INDEX_DIRECTORY


class IngestSettings(BaseModel):
    allow_ext: dict[str, list[str]] = {
        "video": [".mp4", ".mov", ".mkv", ".avi"],
        "image": [".jpg", ".jpeg", ".png", ".webp", ".heic"],
        "audio": [".mp3", ".flac", ".m4a", ".wav", ".ogg"],
    }
    thumb_width: int = 512
    preview_seconds: int = 3


class InternetArchiveSettings(BaseModel):
    email: str = ""
    password: str = ""


class TMDbSettings(BaseModel):
    api_key: str = ""
    access_token: str = ""
    language: str = "en-US"
    include_adult: bool = False


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BITHARBOR_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    server: ServerSettings = ServerSettings()
    db: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    ann: AnnSettings = AnnSettings()
    ingest: IngestSettings = IngestSettings()
    internet_archive: InternetArchiveSettings = InternetArchiveSettings()
    tmdb: TMDbSettings = TMDbSettings()

    def ensure_directories(self) -> None:
        self.server.data_root.mkdir(parents=True, exist_ok=True)
        index_dir = self.ann.index_directory
        index_dir.mkdir(parents=True, exist_ok=True)
        vectors_dir = self.ann.vectors_path.parent
        vectors_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> AppSettings:
    settings = AppSettings()

    # Fallback to legacy environment variables for TMDb credentials
    if not settings.tmdb.api_key:
        legacy_api_key = os.getenv("TMDB_API_KEY")
        if legacy_api_key:
            settings.tmdb.api_key = legacy_api_key
    if not settings.tmdb.access_token:
        legacy_access_token = os.getenv("TMDB_ACCESS_TOKEN")
        if legacy_access_token:
            settings.tmdb.access_token = legacy_access_token

    if not settings.internet_archive.email:
        legacy_email = os.getenv("INTERNET_ARCHIVE_EMAIL")
        if legacy_email:
            settings.internet_archive.email = legacy_email
    if not settings.internet_archive.password:
        legacy_password = os.getenv("INTERNET_ARCHIVE_PASSWORD")
        if legacy_password:
            settings.internet_archive.password = legacy_password

    settings.ensure_directories()
    return settings

