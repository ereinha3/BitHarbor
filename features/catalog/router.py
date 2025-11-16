"""API endpoints for catalog acquisition (Internet Archive, etc.)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.schemas import (
    CatalogSearchRequest,
    CatalogSearchResponse,
    CatalogSearchResult,
    InternetArchiveIngestRequest,
    IngestResponse,
)
from features.auth.dependencies import get_current_admin
from features.catalog.service import CatalogService, get_catalog_service
from api.catalog.internetarchive import InternetArchiveClient, MovieSearchOptions

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/ingest/internet-archive", response_model=IngestResponse)
async def ingest_from_internet_archive(
    payload: InternetArchiveIngestRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> IngestResponse:
    """Download and ingest a movie from Internet Archive.

    This endpoint orchestrates the complete workflow:
    1. Downloads video, poster, and metadata from archive.org
    2. Extracts and maps Internet Archive metadata
    3. Uses search metadata (title/year) for better TMDb matching
    4. Ingests into BitHarbor (includes TMDb enrichment)
    5. Adds to vector search index
    6. Optionally cleans up downloaded files

    The ingested movie will be immediately searchable and enriched with:
    - Internet Archive metadata (title, year, description)
    - TMDb enrichment (cast, crew, ratings, posters, genres)
    - ImageBind embeddings (for semantic search)
    
    **Tip:** Pass `title` and `year` from the search results for better TMDb matching.

    Example:
        ```json
        {
            "identifier": "fantastic-planet__1973",
            "title": "Fantastic Planet",
            "year": 1973,
            "cleanup_after_ingest": true
        }
        ```

    Returns:
        IngestResponse with media_id, file_hash, and vector_hash

    Raises:
        404: Internet Archive item not found
        400: Invalid identifier or download failed
        500: Ingestion failed (file processing, TMDb API, etc.)
    """
    download_dir = Path(payload.download_dir) if payload.download_dir else None

    try:
        result = await catalog_service.ingest_from_internet_archive(
            session=session,
            identifier=payload.identifier,
            search_title=payload.title,
            search_year=payload.year,
            download_dir=download_dir,
            source_type=payload.source_type,
            cleanup_after_ingest=payload.cleanup_after_ingest,
            include_subtitles=payload.include_subtitles,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest from Internet Archive: {str(e)}",
        ) from e


@router.post("/search/internet-archive", response_model=CatalogSearchResponse)
async def search_internet_archive(
    payload: CatalogSearchRequest,
    admin=Depends(get_current_admin),
) -> CatalogSearchResponse:
    """Search Internet Archive movie catalog.

    Search for public domain movies available for download from archive.org.
    Results can be filtered by language, year, and sorted by downloads or other criteria.
    
    **Duplicate Handling:**
    When multiple versions of the same movie exist, results are ranked by:
    - Download count (popularity)
    - Average user rating (quality)
    
    The highest-scoring version appears first.

    Example:
        ```json
        {
            "query": "Metropolis",
            "rows": 10,
            "sorts": ["downloads desc"],
            "filters": ["language:eng", "year:[1920 TO 1930]"]
        }
        ```

    Returns:
        List of search results with identifiers that can be used with
        `/catalog/ingest/internet-archive` endpoint

    Note:
        This endpoint does not download or ingest anything, it only searches.
        Use the returned `identifier` to ingest a movie.
    """
    try:
        ia_client = InternetArchiveClient()

        movies = ia_client.search_movies(
            payload.query,
            limit=payload.rows,
            sorts=payload.sorts,
            filters=payload.filters,
        )

        results: list[CatalogSearchResult] = []
        seen: dict[tuple[str, int | None], CatalogSearchResult] = {}

        for movie in movies:
            identifier = movie.catalog_id or ""
            title = movie.title or identifier
            year = movie.year
            description = movie.overview[:500] if movie.overview else None
            downloads = movie.catalog_downloads

            catalog_result = CatalogSearchResult(
                identifier=identifier,
                title=title,
                year=str(year) if year is not None else None,
                description=description,
                downloads=downloads,
                item_size=None,
                avg_rating=None,
                num_reviews=None,
            )

            key = (title.lower(), year)
            existing = seen.get(key)
            if existing is None or catalog_result.score > existing.score:
                seen[key] = catalog_result

        results = sorted(seen.values(), key=lambda r: r.score, reverse=True)

        return CatalogSearchResponse(results=results, total=len(results))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search Internet Archive: {str(e)}",
        ) from e
