from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False
    data_root: Path = Path("/var/lib/bitharbor")
    pool_root: Path = Path("/mnt/pool")
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
    graph_degree: int = 64
    complexity: int = 100
    search_memory_budget: float = 2.0  # GB
    num_threads: int = 0  # 0 == auto
    rebuild_batch: int = 1
    vectors_path: Path = Path("/var/lib/bitharbor/index/vectors.fp32")
    index_directory: Path = Path("/var/lib/bitharbor/index/diskann")


class IngestSettings(BaseModel):
    allow_ext: dict[str, list[str]] = {
        "video": [".mp4", ".mov", ".mkv", ".avi"],
        "image": [".jpg", ".jpeg", ".png", ".webp", ".heic"],
        "audio": [".mp3", ".flac", ".m4a", ".wav", ".ogg"],
    }
    thumb_width: int = 512
    preview_seconds: int = 3


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

    def ensure_directories(self) -> None:
        self.server.data_root.mkdir(parents=True, exist_ok=True)
        index_dir = self.ann.index_directory
        index_dir.mkdir(parents=True, exist_ok=True)
        vectors_dir = self.ann.vectors_path.parent
        vectors_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.ensure_directories()
    return settings

