from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.ann import get_ann_service
from db.models import MediaCore
from domain.schemas.search import SearchRequest, SearchResult
from infrastructure.embedding import get_embedding_service
from app.settings import AppSettings, get_settings


class SearchService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = get_embedding_service()
        self.ann_service = get_ann_service()

    async def search(self, session: AsyncSession, payload: SearchRequest) -> list[SearchResult]:
        query_vec = self.embedding_service.embed_query_text(payload.query)
        k = payload.k or self.settings.ann.refine_top_k
        candidates = self.ann_service.search(query_vec, k=max(k, self.settings.ann.refine_candidates))
        resolved = await self.ann_service.resolve_media(session, candidates)
        media_ids = [item.media_id for item in resolved if item.media_id]
        if not media_ids:
            return []

        stmt = (
            select(MediaCore)
            .where(MediaCore.media_id.in_(media_ids))
            .options(
                selectinload(MediaCore.movie),
                selectinload(MediaCore.personal_media),
                selectinload(MediaCore.file_path),
            )
        )
        if payload.types:
            stmt = stmt.where(MediaCore.type.in_(payload.types))
        media_rows = await session.scalars(stmt)
        media_map = {media.media_id: media for media in media_rows.all()}

        results: list[SearchResult] = []
        for ann_result in resolved:
            media_id = ann_result.media_id
            if not media_id:
                continue
            media = media_map.get(media_id)
            if not media:
                continue
            title = self._resolve_title(media)
            results.append(
                SearchResult(
                    media_id=media.media_id,
                    score=ann_result.score,
                    type=media.type,
                    title=title,
                    preview_url=None,
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:k]

    def _resolve_title(self, media: MediaCore) -> str:
        if media.movie and media.movie.title:
            return media.movie.title
        if media.personal_media and media.file_path:
            return media.file_path.abs_path.split("/")[-1]
        return media.media_id


_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service

