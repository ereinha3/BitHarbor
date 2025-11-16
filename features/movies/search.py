from __future__ import annotations

from typing import Callable, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends

from app.settings import AppSettings, get_settings
from api.catalog.internetarchive import InternetArchiveClient
from api.metadata.tmdb.client import TMDbClient
from domain.catalog import CatalogMatch, CatalogMatchCandidate, CatalogMatchResponse
from domain.media.movies import MovieMedia

_MATCH_REGISTRY: Dict[str, CatalogMatch] = {}


def get_registered_match(match_key: str) -> CatalogMatch | None:
    """Return a previously registered catalog match."""

    return _MATCH_REGISTRY.get(match_key)


def clear_registered_matches() -> None:
    """Clear the in-memory match registry (useful for tests)."""

    _MATCH_REGISTRY.clear()


class MovieCatalogSearchService:
    """Service that matches TMDb search results against Internet Archive assets."""

    def __init__(
        self,
        settings: AppSettings,
        ia_client: InternetArchiveClient | None = None,
        tmdb_client_factory: Callable[[], TMDbClient] | None = None,
    ) -> None:
        self.settings = settings
        self.ia_client = ia_client or InternetArchiveClient()
        self._tmdb_client_factory = tmdb_client_factory

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        year: Optional[int] = None,
    ) -> CatalogMatchResponse:
        if not (self.settings.tmdb.api_key or self.settings.tmdb.access_token):
            raise RuntimeError("TMDb credentials are required for catalog matching")

        tmdb_client = (
            self._tmdb_client_factory()
            if self._tmdb_client_factory is not None
            else TMDbClient()
        )

        try:
            tmdb_movies = await tmdb_client.search_movie(
                query,
                limit=limit,
                year=year,
                include_adult=self.settings.tmdb.include_adult,
                language=self.settings.tmdb.language,
            )
        finally:
            await tmdb_client.close()

        ia_movies = self.ia_client.search_movies(
            query,
            limit=max(limit * 3, 5),
            sorts=["num_favorites desc", "downloads desc"],
            filters=None,
        )

        matches: List[CatalogMatch] = []
        for tmdb_movie in tmdb_movies:
            if tmdb_movie.year is None:
                continue
            if year is not None and tmdb_movie.year != year:
                continue

            candidates = self._match_candidates(tmdb_movie, ia_movies)
            if not candidates:
                continue

            match_key = uuid4().hex
            tmdb_id = self._safe_int(tmdb_movie.catalog_id)
            catalog_match = CatalogMatch(
                match_key=match_key,
                tmdb_id=tmdb_id,
                tmdb_movie=tmdb_movie,
                best_candidate=candidates[0],
                candidates=candidates,
            )
            _MATCH_REGISTRY[match_key] = catalog_match
            matches.append(catalog_match)

            if len(matches) >= limit:
                break

        return CatalogMatchResponse(matches=matches, total=len(matches))

    def _match_candidates(
        self,
        tmdb_movie: MovieMedia,
        ia_movies: List[MovieMedia],
    ) -> List[CatalogMatchCandidate]:
        filtered = [
            movie
            for movie in ia_movies
            if movie.year is not None
            and movie.catalog_id
            and movie.year == tmdb_movie.year
        ]
        if not filtered:
            return []

        filtered.sort(key=lambda m: m.catalog_downloads or 0, reverse=True)
        max_downloads = filtered[0].catalog_downloads or 0

        candidates: List[CatalogMatchCandidate] = []
        for movie in filtered:
            downloads = movie.catalog_downloads or 0
            score = (downloads / max_downloads) if max_downloads else 0.0
            candidates.append(
                CatalogMatchCandidate(
                    identifier=movie.catalog_id or "",
                    score=min(1.0, score),
                    downloads=downloads,
                    movie=movie,
                )
            )
        return candidates

    @staticmethod
    def _safe_int(value: Optional[str]) -> int:
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0


def get_movie_catalog_search_service(
    settings: AppSettings = Depends(get_settings),
) -> MovieCatalogSearchService:
    return MovieCatalogSearchService(settings)
