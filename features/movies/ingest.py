from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app.settings import get_settings
from features.movies.vector_index import append as append_vector
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service
from utils.hashing import blake3_file


@dataclass(slots=True)
class MovieIngestResult:
    file_hash: str
    video_path: Path
    vector_hash: str
    vector_row_id: int
    metadata: Mapping[str, object]


_settings = get_settings()
_text_embedding_service = get_sentence_bert_service()
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

    title = str(metadata.get("title", "")).strip()
    overview = str(metadata.get("overview", "")).strip()
    genres = metadata.get("genres") or []
    if isinstance(genres, (list, tuple)):
        genres_text = " ".join(str(g) for g in genres if g)
    else:
        genres_text = str(genres)

    components = [title, overview, genres_text]
    text_blob = " ".join(filter(None, components)).strip()
    if not text_blob:
        text_blob = stored_path.stem.replace("_", " ")

    embedding = _text_embedding_service.encode(text_blob)
    vector_row_id = append_vector(embedding.vector)

    return MovieIngestResult(
        file_hash=file_hash,
        video_path=stored_path,
        vector_hash=embedding.vector_hash,
        vector_row_id=vector_row_id,
        metadata=metadata,
    )

