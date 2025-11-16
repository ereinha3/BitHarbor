from __future__ import annotations

import asyncio

import pytest

from api.metadata.tmdb.client import TMDbClient, TMDbMovieMatch


def test_search_movies_with_metadata_maps_to_movie_media(monkeypatch) -> None:
    client = TMDbClient(api_key="dummy")

    sample_response = {
        "page": 1,
        "total_pages": 1,
        "results": [
            {
                "id": 603,
                "title": "The Matrix",
                "original_title": "The Matrix",
                "release_date": "1999-03-31",
                "overview": "Set in the future, Neo discovers the truth about the Matrix.",
                "poster_path": "/poster.jpg",
                "backdrop_path": "/backdrop.jpg",
                "popularity": 100.1,
                "vote_average": 8.7,
                "vote_count": 23000,
                "adult": False,
                "original_language": "en",
                "genre_ids": [28, 878],
            }
        ],
    }

    async def fake_request(method: str, endpoint: str, params: dict[str, object]) -> dict[str, object]:
        assert endpoint == "search/movie"
        return sample_response

    monkeypatch.setattr(client, "_request", fake_request)

    matches = asyncio.run(client.search_movies_with_metadata("matrix", limit=5))

    assert matches, "Expected at least one match"
    match = matches[0]
    assert isinstance(match, TMDbMovieMatch)
    assert match.tmdb_id == 603
    movie = match.movie
    assert movie.media_type == "movie"
    assert movie.title == "The Matrix"
    assert movie.year == 1999
    assert movie.vote_average == pytest.approx(8.7)
    assert movie.poster and movie.poster.file_path.endswith("/poster.jpg")

    asyncio.run(client.close())
