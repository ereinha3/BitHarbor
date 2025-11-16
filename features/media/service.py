from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import MediaCore, Movie, PersonalMedia
from domain.schemas.enrichment import EnrichedMetadata, MovieMetadata
from domain.schemas.media import MediaDetail, MediaListResponse, MediaSummary
from domain.schemas.ingest import MediaTypeLiteral

logger = logging.getLogger(__name__)


class MediaService:
    def __init__(self) -> None:
        pass

    async def get_media(
        self, session: AsyncSession, media_id: str
    ) -> MediaCore:
        stmt = (
            select(MediaCore)
            .where(MediaCore.media_id == media_id)
            .options(
                selectinload(MediaCore.movie),
                selectinload(MediaCore.personal_media),
                selectinload(MediaCore.file_path),
            )
        )
        media = await session.scalar(stmt)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found.")
        return media

    async def get_media_detail(
        self, session: AsyncSession, media_id: str
    ) -> MediaDetail:
        media = await self.get_media(session, media_id)
        metadata = self._extract_metadata(media)
        enriched_metadata = self._extract_enriched_metadata(media)
        title = self._resolve_title(media)
        return MediaDetail(
            media_id=media.media_id,
            type=media.type,
            title=title,
            source_type=media.source_type,
            vector_hash=media.vector_hash,
            file_hash=media.file_hash,
            metadata=metadata,
            enriched_metadata=enriched_metadata,
        )

    async def list_media(
        self,
        session: AsyncSession,
        media_type: Optional[MediaTypeLiteral],
        limit: int,
        offset: int,
    ) -> MediaListResponse:
        stmt = select(MediaCore).options(
            selectinload(MediaCore.movie),
            selectinload(MediaCore.personal_media),
            selectinload(MediaCore.file_path),
        ).order_by(MediaCore.created_at.desc())
        count_stmt = select(func.count(MediaCore.media_id))
        if media_type:
            stmt = stmt.where(MediaCore.type == media_type)
            count_stmt = count_stmt.where(MediaCore.type == media_type)
        stmt = stmt.limit(limit).offset(offset)
        rows = await session.scalars(stmt)
        items = [
            MediaSummary(
                media_id=media.media_id,
                type=media.type,
                title=self._resolve_title(media),
                source_type=media.source_type,
                vector_hash=media.vector_hash,
            )
            for media in rows.all()
        ]
        total = await session.scalar(count_stmt) or 0
        return MediaListResponse(items=items, total=total)

    async def stream_media(self, session: AsyncSession, media_id: str) -> FileResponse:
        media = await self.get_media(session, media_id)
        if not media.file_path:
            raise HTTPException(status_code=404, detail="File path not found.")
        file_path = Path(media.file_path.abs_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file missing on disk.")
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    def _extract_metadata(self, media: MediaCore) -> Optional[Dict[str, Any]]:
        """Extract raw metadata from database (legacy field)."""
        if media.movie and media.movie.metadata_enriched:
            try:
                return json.loads(media.movie.metadata_enriched)
            except json.JSONDecodeError:
                return None
        return None

    def _extract_enriched_metadata(self, media: MediaCore) -> Optional[EnrichedMetadata]:
        """Extract and parse type-safe enriched metadata.
        
        Parses the metadata_enriched JSON field and validates it against
        the appropriate Pydantic schema based on media type.
        """
        try:
            if media.type == "movie" and media.movie:
                if media.movie.metadata_enriched:
                    # Parse JSON and validate as MovieMetadata
                    movie_data = json.loads(media.movie.metadata_enriched)
                    movie_metadata = MovieMetadata(**movie_data)
                    return EnrichedMetadata(movie=movie_metadata)
            
            # Add other media types here when their enrichment is implemented
            # elif media.type == "tv" and media.tv_episode:
            #     ...
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse metadata_enriched JSON for {media.media_id}: {e}")
        except Exception as e:
            logger.warning(f"Failed to validate enriched metadata for {media.media_id}: {e}")
        
        return None

    def _resolve_title(self, media: MediaCore) -> str:
        if media.movie and media.movie.title:
            return media.movie.title
        if media.personal_media and media.file_path:
            return Path(media.file_path.abs_path).name
        return media.media_id


_media_service: MediaService | None = None


def get_media_service() -> MediaService:
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service

