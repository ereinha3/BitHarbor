from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.catalog import (
    CatalogDownloadRequest,
    CatalogDownloadResponse,
    CatalogMatchResponse,
)

from .download import (
    CatalogMatchNotFoundError,
    MovieCatalogDownloadService,
    get_movie_catalog_download_service,
)
from .ingest import ingest_catalog_movie
from .search import (
    MovieCatalogSearchService,
    get_movie_catalog_search_service,
    get_registered_match,
)

router = APIRouter(prefix="/movies", tags=["movies"])


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
    session: AsyncSession = Depends(get_session),
    download_service: MovieCatalogDownloadService = Depends(get_movie_catalog_download_service),
) -> CatalogDownloadResponse:
    """Plan or execute a catalog-based download using a match key."""

    destination_path = Path(payload.destination).expanduser().resolve() if payload.destination else None

    if not payload.execute:
        try:
            return download_service.plan(payload.match_key, destination=destination_path)
        except CatalogMatchNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        download_result = download_service.download(payload.match_key, destination=destination_path)
    except CatalogMatchNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    match = get_registered_match(payload.match_key)
    if match is None:
        raise HTTPException(status_code=404, detail="Catalog match no longer available")

    if not download_result.video_path:
        raise HTTPException(status_code=500, detail="Download did not produce a video file")

    poster_path: Path | None = None
    if download_result.cover_art_file:
        base_dir = Path(download_result.video_path).parent
        candidate = base_dir / download_result.cover_art_file
        if candidate.exists():
            poster_path = candidate

    tmdb_movie = match.tmdb_movie
    metadata = {
        "title": tmdb_movie.title,
        "overview": tmdb_movie.overview,
        "genres": tmdb_movie.genres,
        "languages": tmdb_movie.languages,
        "year": tmdb_movie.year,
        "poster_path": str(poster_path) if poster_path else None,
        "poster": tmdb_movie.poster.model_dump() if tmdb_movie.poster else None,
        "backdrop": tmdb_movie.backdrop.model_dump() if tmdb_movie.backdrop else None,
        "runtime_min": tmdb_movie.runtime_min,
        "release_date": tmdb_movie.release_date,
        "vote_average": tmdb_movie.vote_average,
        "vote_count": tmdb_movie.vote_count,
        "cast": tmdb_movie.cast,
        "rating": tmdb_movie.rating,
        "catalog_source": tmdb_movie.catalog_source or "tmdb",
        "catalog_id": tmdb_movie.catalog_id,
        "tmdb_id": match.tmdb_id,
        "ia_identifier": match.best_candidate.identifier,
        "ia_downloads": match.best_candidate.downloads,
        "ia_score": match.best_candidate.score,
    }

    try:
        ingest_result = await ingest_catalog_movie(
            session=session,
            video_path=Path(download_result.video_path),
            metadata=metadata,
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    download_result.file_hash = ingest_result.file_hash
    download_result.vector_hash = ingest_result.vector_hash
    download_result.vector_row_id = ingest_result.vector_row_id
    download_result.movie_id = ingest_result.movie_id
    download_result.created = ingest_result.created
    return download_result
