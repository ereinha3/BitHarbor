from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app.settings import get_settings
from features.movies.vector_index import append as append_vector
from infrastructure.embedding import get_embedding_service
from utils.hashing import blake3_file


@dataclass(slots=True)
class MovieIngestResult:
    file_hash: str
    video_path: Path
    vector_hash: str
    vector_row_id: int
    metadata: Mapping[str, object]


_settings = get_settings()
_embedding_service = get_embedding_service()
_raid_root = Path(os.environ.get("RAID_PATH", str(_settings.server.pool_root)))


def _store_video_on_raid(source: Path, file_hash: str) -> Path:
    suffix = source.suffix.lower()
    shard = file_hash[:2]
    dest_dir = _raid_root / "movies" / shard
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_hash}{suffix}"
    if not dest.exists():
        shutil.copy2(source, dest)
    return dest


def ingest_catalog_movie(*, video_path: Path, metadata: Mapping[str, object]) -> MovieIngestResult:
    video_path = video_path.expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found at {video_path}")

    file_hash = blake3_file(video_path)
    stored_path = _store_video_on_raid(video_path, file_hash)

    text_blob_parts = [
        str(metadata.get("title", "")),
        str(metadata.get("overview", "")),
        json.dumps(metadata.get("genres", [])),
    ]
    text_blob = " ".join(filter(None, text_blob_parts)).strip()
    if not text_blob:
        text_blob = stored_path.stem.replace("_", " ")

    poster_path = metadata.get("poster_path")
    if poster_path:
        poster_path = Path(poster_path)
        if not poster_path.exists():
            poster_path = None
    else:
        poster_path = None

    embedding = _embedding_service.embed_catalog(text_blob=text_blob, poster_path=poster_path)
    vector_row_id = append_vector(embedding.vector)

    return MovieIngestResult(
        file_hash=file_hash,
        video_path=stored_path,
        vector_hash=embedding.vector_hash,
        vector_row_id=vector_row_id,
        metadata=metadata,
    )

