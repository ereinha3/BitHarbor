from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.catalog import (
    CatalogDownloadRequest,
    CatalogDownloadResponse,
    CatalogMatchResponse,
)
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
from features.movies.download import (
    CatalogMatchNotFoundError,
    MovieCatalogDownloadService,
    get_movie_catalog_download_service,
)
from features.movies.search import MovieCatalogSearchService, get_movie_catalog_search_service
from features.search.service import SearchService, get_search_service

router = APIRouter(prefix="/movies", tags=["movies"])


@router.post("/search", response_model=SearchResponse)
async def search_movies(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Vector search across movie library"""
    # Force filter to only movie type
    payload.types = ["movie"]
    results = await search_service.search(session, payload)
    return SearchResponse(results=results)


@router.get("/media", response_model=MediaListResponse)
async def list_movies(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaListResponse:
    """List all movie media items"""
    return await media_service.list_media(session, "movie", limit, offset)


@router.get("/media/{media_id}", response_model=MediaDetail)
async def get_movie_detail(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> MediaDetail:
    """Fetch metadata details for a specific movie"""
    return await media_service.get_media_detail(session, media_id)


@router.get("/media/{media_id}/stream")
async def stream_movie(
    media_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    media_service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Stream original movie media file"""
    return await media_service.stream_media(session, media_id)


@router.post("/ingest/start", response_model=IngestResponse)
async def ingest_movie(
    payload: IngestRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    ingest_service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    """Ingest a movie file into the library"""
    # Force media type to movie
    payload.media_type = "movie"
    return await ingest_service.ingest(session, payload)


@router.get("/catalog/search", response_model=CatalogMatchResponse)
async def search_catalog_movies(
    query: str = Query(..., min_length=1, description="Movie title to search in catalog sources"),
    limit: int = Query(10, ge=1, le=50),
    year: int | None = Query(None, description="Restrict matches to a specific release year"),
    search_service: MovieCatalogSearchService = Depends(get_movie_catalog_search_service),
) -> CatalogMatchResponse:
    """Search TMDb and Internet Archive for catalog matches."""

    try:
        return await search_service.search(query=query, limit=limit, year=year)
    except RuntimeError as exc:  # missing TMDb creds
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/catalog/download", response_model=CatalogDownloadResponse)
async def download_catalog_movie(
    payload: CatalogDownloadRequest,
    download_service: MovieCatalogDownloadService = Depends(get_movie_catalog_download_service),
) -> CatalogDownloadResponse:
    """Plan or execute a catalog-based download using a match key."""

    destination_path = Path(payload.destination).expanduser().resolve() if payload.destination else None

    try:
        if payload.execute:
            return download_service.download(payload.match_key, destination=destination_path)
        return download_service.plan(payload.match_key, destination=destination_path)
    except CatalogMatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
