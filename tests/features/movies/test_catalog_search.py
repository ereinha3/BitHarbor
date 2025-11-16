from __future__ import annotations

import asyncio

import pytest

from app.settings import AppSettings
from domain.catalog import CatalogMatch
from domain.media.movies import MovieMedia
from features.movies.search import (
    MovieCatalogSearchService,
    clear_registered_matches,
    get_registered_match,
)


class StubTMDbClient:
    def __init__(self, movies: list[MovieMedia]) -> None:
        self._movies = movies

    async def search_movie(self, *_args, **_kwargs) -> list[MovieMedia]:
        return self._movies

    async def close(self) -> None:  # noqa: D401
        return None


class StubIAClient:
    def __init__(self, movies: list[MovieMedia]) -> None:
        self._movies = movies

    def search_movies(self, *_args, **_kwargs) -> list[MovieMedia]:
        return self._movies


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    clear_registered_matches()


def test_catalog_search_matches_by_year() -> None:
    settings = AppSettings()
    settings.tmdb.api_key = "dummy"

    tmdb_movie = MovieMedia(
        title="The Matrix",
        media_type="movie",
        catalog_source="tmdb",
        catalog_id="603",
        year=1999,
    )

    ia_movies = [
        MovieMedia(
            title="The Matrix",
            media_type="movie",
            catalog_source="internet_archive",
            catalog_id="ia-1",
            year=1999,
            catalog_downloads=120,
        ),
        MovieMedia(
            title="The Matrix (alt)",
            media_type="movie",
            catalog_source="internet_archive",
            catalog_id="ia-2",
            year=1999,
            catalog_downloads=45,
        ),
    ]

    service = MovieCatalogSearchService(
        settings,
        ia_client=StubIAClient(ia_movies),
        tmdb_client_factory=lambda: StubTMDbClient([tmdb_movie]),
    )

    response = asyncio.run(service.search("matrix", limit=3))

    assert response.total == 1
    match = response.matches[0]
    assert match.best_candidate.identifier == "ia-1"
    assert match.best_candidate.downloads == 120
    registry_entry: CatalogMatch | None = get_registered_match(match.match_key)
    assert registry_entry is not None
    assert registry_entry.tmdb_movie.title == "The Matrix"


def test_catalog_search_skips_when_no_year_match() -> None:
    settings = AppSettings()
    settings.tmdb.api_key = "dummy"

    tmdb_movie = MovieMedia(
        title="Example",
        media_type="movie",
        catalog_source="tmdb",
        catalog_id="1",
        year=2000,
    )

    ia_movie = MovieMedia(
        title="Example",
        media_type="movie",
        catalog_source="internet_archive",
        catalog_id="ia",
        year=1999,
        catalog_downloads=10,
    )

    service = MovieCatalogSearchService(
        settings,
        ia_client=StubIAClient([ia_movie]),
        tmdb_client_factory=lambda: StubTMDbClient([tmdb_movie]),
    )

    response = asyncio.run(service.search("example", limit=3))
    assert response.total == 0
