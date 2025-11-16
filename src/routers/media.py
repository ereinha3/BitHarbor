from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from bitharbor.db.session import get_session
from bitharbor.schemas import MediaDetail, MediaListResponse
from bitharbor.schemas.ingest import MediaTypeLiteral
from bitharbor.services.auth.dependencies import get_current_admin
from bitharbor.services.media.service import MediaService, get_media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("", response_model=MediaListResponse)
async def list_media(
    media_type: Optional[MediaTypeLiteral] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaListResponse:
    return await media_service.list_media(session, media_type, limit, offset)


@router.get("/{media_id}", response_model=MediaDetail)
async def get_media_detail(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaDetail:
    return await media_service.get_media_detail(session, media_id)


@router.get("/{media_id}/stream")
async def stream_media(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> FileResponse:
    return await media_service.stream_media(session, media_id)

