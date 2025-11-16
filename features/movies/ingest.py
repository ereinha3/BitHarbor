from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import get_settings
from db.models import IdMap, Movie
from features.movies.vector_index import append as append_vector
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service
from utils.hashing import blake3_file


@dataclass(slots=True)
class MovieIngestResult:
    file_hash: str
    video_path: Path
    vector_hash: str | None
    vector_row_id: int | None
    movie_id: int
    created: bool
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


async def ingest_catalog_movie(
    *,
    session: AsyncSession,
    video_path: Path,
    metadata: Mapping[str, object],
) -> MovieIngestResult:
    metadata_dict = dict(metadata)
    video_path = video_path.expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found at {video_path}")

    file_hash = blake3_file(video_path)

    existing_result = await session.execute(
        select(Movie).where(Movie.file_hash == file_hash)
    )
    existing_movie = existing_result.scalar_one_or_none()
    if existing_movie:
        existing_path = (
            Path(existing_movie.path)
            if existing_movie.path
            else video_path
        )
        return MovieIngestResult(
            file_hash=file_hash,
            video_path=existing_path,
            vector_hash=existing_movie.embedding_hash,
            vector_row_id=None,
            movie_id=existing_movie.id,
            created=False,
            metadata=metadata_dict,
        )

    title = str(metadata_dict.get("title", "")).strip()
    overview = str(metadata_dict.get("overview", "")).strip()
    genres = metadata_dict.get("genres") or []
    if isinstance(genres, (list, tuple)):
        genres_text = " ".join(str(g) for g in genres if g)
    else:
        genres_text = str(genres)

    components = [title, overview, genres_text]
    text_blob = " ".join(filter(None, components)).strip()
    if not text_blob:
        text_blob = video_path.stem.replace("_", " ")

    embedding = _text_embedding_service.encode(text_blob)

    embedding_result = await session.execute(
        select(Movie).where(Movie.embedding_hash == embedding.vector_hash)
    )
    embedding_movie = embedding_result.scalar_one_or_none()
    if embedding_movie:
        existing_path = (
            Path(embedding_movie.path)
            if embedding_movie.path
            else video_path
        )
        return MovieIngestResult(
            file_hash=embedding_movie.file_hash or file_hash,
            video_path=existing_path,
            vector_hash=embedding_movie.embedding_hash,
            vector_row_id=None,
            movie_id=embedding_movie.id,
            created=False,
            metadata=metadata_dict,
        )

    stored_path = _store_video_on_raid(video_path, file_hash)
    vector_row_id = append_vector(embedding.vector)

    poster_struct = metadata_dict.get("poster")
    if not poster_struct and metadata_dict.get("poster_path"):
        poster_struct = {"file_path": metadata_dict["poster_path"]}

    movie = Movie(
        file_hash=file_hash,
        embedding_hash=embedding.vector_hash,
        path=str(stored_path),
        format=stored_path.suffix.lstrip("."),
        media_type="movie",
        catalog_source=metadata_dict.get("catalog_source") or "tmdb",
        catalog_id=str(metadata_dict.get("tmdb_id") or metadata_dict.get("catalog_id") or ""),
        catalog_score=metadata_dict.get("ia_score"),
        catalog_downloads=metadata_dict.get("ia_downloads"),
        title=title or stored_path.stem.replace("_", " "),
        overview=overview or metadata_dict.get("overview"),
        tagline=metadata_dict.get("tagline"),
        release_date=metadata_dict.get("release_date"),
        year=metadata_dict.get("year"),
        runtime_min=metadata_dict.get("runtime_min"),
        genres=metadata_dict.get("genres"),
        languages=metadata_dict.get("languages"),
        vote_average=metadata_dict.get("vote_average"),
        vote_count=metadata_dict.get("vote_count"),
        cast=metadata_dict.get("cast"),
        rating=metadata_dict.get("rating"),
        poster=poster_struct,
        backdrop=metadata_dict.get("backdrop"),
    )
    session.add(movie)
    await session.flush()

    if vector_row_id is not None:
        session.add(
            IdMap(
                row_id=vector_row_id,
                vector_hash=embedding.vector_hash,
                media_id=str(movie.id),
            )
        )

    return MovieIngestResult(
        file_hash=file_hash,
        video_path=stored_path,
        vector_hash=embedding.vector_hash,
        vector_row_id=vector_row_id,
        movie_id=movie.id,
        created=True,
        metadata=metadata_dict,
    )

