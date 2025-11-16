from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.schemas import (
    IngestRequest,
    IngestResponse,
    MediaDetail,
    MediaListResponse,
    SearchRequest,
    SearchResponse,
)
from features.auth.dependencies import get_current_admin
from features.ingest.service import IngestService, get_ingest_service
from features.media.service import MediaService, get_media_service
from features.search.service import SearchService, get_search_service

router = APIRouter(prefix="/music", tags=["music"])


@router.post("/search", response_model=SearchResponse)
async def search_music(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Vector search across music library"""
    # Force filter to only music type
    payload.types = ["music"]
    results = await search_service.search(session, payload)
    return SearchResponse(results=results)


@router.get("/media", response_model=MediaListResponse)
async def list_music(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaListResponse:
    """List all music track media items"""
    return await media_service.list_media(session, "music", limit, offset)


@router.get("/media/{media_id}", response_model=MediaDetail)
async def get_music_detail(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaDetail:
    """Fetch metadata details for a specific music track"""
    return await media_service.get_media_detail(session, media_id)


@router.get("/media/{media_id}/stream")
async def stream_music(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Stream original music track media file"""
    return await media_service.stream_media(session, media_id)


@router.post("/ingest/start", response_model=IngestResponse)
async def ingest_music(
    payload: IngestRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    ingest_service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    """Ingest a music track file into the library"""
    # Force media type to music
    payload.media_type = "music"
    return await ingest_service.ingest(session, payload)
