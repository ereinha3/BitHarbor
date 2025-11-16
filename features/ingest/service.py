from __future__ import annotations

import math
import json
import logging
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ann import get_ann_service
from db.models import FilePath, MediaCore, Movie, PersonalMedia
from domain.schemas import IngestRequest, IngestResponse
from infrastructure.embedding import get_embedding_service
from features.ingest.metadata import (
    build_text_blob,
    compute_meta_fingerprint,
    serialize_metadata,
)
from features.ingest.enrichment import get_enrichment_service
from infrastructure.storage.content_addressable import ContentAddressableStorage
from app.settings import AppSettings, get_settings
from utils.hashing import blake3_file

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = get_embedding_service()
        self.ann_service = get_ann_service()
        self.enrichment_service = get_enrichment_service()
        self.storage = ContentAddressableStorage(self.settings)
        self.ext_to_modality = self._build_extension_map()

    def _build_extension_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for modality, extensions in self.settings.ingest.allow_ext.items():
            for ext in extensions:
                mapping[ext.lower()] = modality
        return mapping

    def _detect_modality(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext not in self.ext_to_modality:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension: {ext}",
            )
        return self.ext_to_modality[ext]

    async def ingest(self, session: AsyncSession, payload: IngestRequest) -> IngestResponse:
        source_path = Path(payload.path).expanduser().resolve()
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found.")

        modality = self._detect_modality(source_path)
        file_hash = blake3_file(source_path)
        stored_path = self.storage.store(source_path, modality, file_hash)

        file_path = await self._get_or_create_file_path(session, modality, file_hash, stored_path)
        metadata = payload.metadata or {}
        fallback = source_path.stem.replace("_", " ")
        text_blob = build_text_blob(metadata, fallback=fallback)
        meta_fingerprint = compute_meta_fingerprint(text_blob)
        metadata_raw = serialize_metadata(metadata)

        poster_path = Path(payload.poster_path).expanduser().resolve() if payload.poster_path else None

        if payload.media_type == "personal":
            embedding = self.embedding_service.embed_personal_media(stored_path)
            embedding_source = "content"
        else:
            embedding = self.embedding_service.embed_catalog(
                text_blob=text_blob,
                poster_path=poster_path if poster_path and poster_path.exists() else None,
            )
            embedding_source = "text+image" if poster_path else "text"

        media_id = str(uuid4())
        media_core = MediaCore(
            media_id=media_id,
            type=payload.media_type,
            file_hash=file_hash,
            vector_hash=embedding.vector_hash,
            source_type=payload.source_type,
            embedding_source=embedding_source,
            hdd_path_id=file_path.hdd_path_id,
            preview_path=None,
        )
        session.add(media_core)
        await session.flush()

        await self._create_type_record(
            session=session,
            media_type=payload.media_type,
            media_id=media_id,
            metadata=metadata,
            meta_fingerprint=meta_fingerprint,
            metadata_raw=metadata_raw,
            text_blob=text_blob,
        )

        await self.ann_service.add_embedding(
            session=session,
            media_id=media_id,
            vector_hash=embedding.vector_hash,
            vector=embedding.vector,
        )

        await session.commit()

        return IngestResponse(media_id=media_id, file_hash=file_hash, vector_hash=embedding.vector_hash)

    async def _get_or_create_file_path(
        self,
        session: AsyncSession,
        modality: str,
        file_hash: str,
        stored_path: Path,
    ) -> FilePath:
        stmt = select(FilePath).where(FilePath.file_hash == file_hash)
        existing = await session.scalar(stmt)
        if existing:
            return existing
        file_path = FilePath(
            file_hash=file_hash,
            modality=modality,
            abs_path=str(stored_path),
            size_bytes=stored_path.stat().st_size,
        )
        session.add(file_path)
        await session.flush()
        return file_path

    async def _create_type_record(
        self,
        session: AsyncSession,
        media_type: str,
        media_id: str,
        metadata: Mapping[str, Any],
        meta_fingerprint: str,
        metadata_raw: str | None,
        text_blob: str,
    ) -> None:
        if media_type == "movie":
            # Try to enrich with TMDb metadata
            enriched_data = await self._enrich_movie_metadata(metadata, text_blob)
            
            if enriched_data:
                # Use enriched data from TMDb
                logger.info(f"Using enriched TMDb metadata for movie: {enriched_data.get('title')}")
                movie = Movie(
                    media_id=media_id,
                    tmdb_id=enriched_data.get("tmdb_id"),
                    imdb_id=enriched_data.get("imdb_id"),
                    title=enriched_data.get("title"),
                    original_title=enriched_data.get("original_title"),
                    year=enriched_data.get("year"),
                    release_date=enriched_data.get("release_date"),
                    runtime_min=enriched_data.get("runtime_min"),
                    genres=enriched_data.get("genres"),
                    languages=enriched_data.get("languages"),
                    countries=enriched_data.get("countries"),
                    overview=enriched_data.get("overview"),
                    tagline=enriched_data.get("tagline"),
                    cast_json=enriched_data.get("cast_json"),
                    crew_json=enriched_data.get("crew_json"),
                    posters_json=enriched_data.get("posters_json"),
                    backdrops_json=enriched_data.get("backdrops_json"),
                    meta_fingerprint=meta_fingerprint,
                    metadata_raw=metadata_raw,
                    metadata_enriched=enriched_data.get("metadata_enriched"),
                )
            else:
                # Fallback to basic metadata if enrichment fails
                logger.warning(f"TMDb enrichment failed, using basic metadata for: {text_blob}")
                movie = Movie(
                    media_id=media_id,
                    title=str(metadata.get("title") or text_blob.title()),
                    original_title=metadata.get("original_title"),
                    overview=metadata.get("overview"),
                    year=metadata.get("year"),
                    genres=self._pipe_join(metadata.get("genres")),
                    languages=self._pipe_join(metadata.get("languages")),
                    countries=self._pipe_join(metadata.get("countries")),
                    meta_fingerprint=meta_fingerprint,
                    metadata_raw=metadata_raw,
                    metadata_enriched=metadata_raw,
                )
            session.add(movie)
            
        elif media_type == "tv":
            # TODO: Implement TV show enrichment
            logger.info("TV show enrichment not yet implemented, using basic metadata")
            # For now, create basic record (you'll need to handle TvEpisode differently)
            pass
            
        elif media_type == "personal":
            persons = metadata.get("persons")
            personal = PersonalMedia(
                media_id=media_id,
                device_make=metadata.get("device_make"),
                device_model=metadata.get("device_model"),
                album_name=metadata.get("album_name"),
                orientation=metadata.get("orientation"),
                persons_json=json.dumps(persons, ensure_ascii=False) if persons else None,
            )
            session.add(personal)
        else:
            # Other types can be implemented later; store metadata via movie table fallback if desired.
            pass

    async def _enrich_movie_metadata(
        self, 
        metadata: Mapping[str, Any], 
        text_blob: str
    ) -> dict[str, Any] | None:
        """Attempt to enrich movie metadata using TMDb API.
        
        Args:
            metadata: Original metadata from ingest request
            text_blob: Fallback title if metadata doesn't have title
            
        Returns:
            Dictionary with enriched metadata or None if enrichment fails
        """
        # Extract title and year from metadata or text_blob
        title = metadata.get("title") or text_blob.title()
        year = metadata.get("year")
        
        if not title:
            logger.warning("No title available for TMDb enrichment")
            return None
        
        try:
            # Attempt to enrich with TMDb
            enrichment_result = await self.enrichment_service.enrich_movie(
                title=title,
                year=year,
                include_credits=True,
                include_images=True,
            )
            
            if enrichment_result:
                return enrichment_result.to_movie_dict()
            
        except Exception as e:
            logger.error(f"Error during TMDb enrichment for '{title}': {e}")
        
        return None

    def _pipe_join(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            joined = "|".join(str(item).strip() for item in value if item not in (None, ""))
            return joined or None
        return str(value)


_ingest_service: IngestService | None = None


def get_ingest_service() -> IngestService:
    global _ingest_service
    if _ingest_service is None:
        _ingest_service = IngestService()
    return _ingest_service

