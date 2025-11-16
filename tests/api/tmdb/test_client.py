"""Example usage and tests for the TMDb API client."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.tmdb import TMDbClient

# Get env variables from .env
import dotenv

dotenv.load_dotenv()


async def test_search_movie():
    """Test movie search functionality."""
    # Get API credentials from .env
    api_key = os.getenv("TMDB_API_KEY", "")
    access_token = os.getenv("TMDB_ACCESS_TOKEN", "")

    if not api_key and not access_token:
        print("⚠️  No TMDb credentials found. Set TMDB_API_KEY or TMDB_ACCESS_TOKEN")
        return

    async with TMDbClient(api_key=api_key, access_token=access_token) as client:
        print("\n🔍 Searching for 'The Matrix'...")
        movies = await client.search_movie("The Matrix", year=1999, limit=5)

        print(f"Found {len(movies)} results:\n")
        for i, movie in enumerate(movies, 1):
            print(f"{i}. {movie.title} ({movie.year})")
            print(f"   TMDb ID: {movie.catalog_id}")
            print(f"   Rating: {movie.vote_average}/10 ({movie.vote_count} votes)")
            print(f"   Overview: {movie.overview[:100]}..." if movie.overview else "   Overview: n/a")
            if movie.poster and movie.poster.file_path:
                print(f"   Poster: {movie.poster.file_path}")
            print()


async def test_movie_details():
    """Test fetching detailed movie information."""
    api_key = os.getenv("TMDB_API_KEY", "")
    access_token = os.getenv("TMDB_ACCESS_TOKEN", "")

    if not api_key and not access_token:
        print("⚠️  No TMDb credentials found. Set TMDB_API_KEY or TMDB_ACCESS_TOKEN")
        return

    async with TMDbClient(api_key=api_key, access_token=access_token) as client:
        movie_id = 603  # The Matrix (1999)
        print(f"\n📽️  Fetching details for movie ID {movie_id}...")

        movie = await client.get_movie_details(
            movie_id, append_to_response=["videos", "credits"]
        )

        print(f"\nTitle: {movie.title}")
        print(f"Original Title: {movie.title}")
        print(f"Tagline: {movie.tagline}")
        print(f"Release Year: {movie.year}")
        print(f"Runtime: {movie.runtime_min} minutes")
        print(f"Rating: {movie.vote_average}/10 ({movie.vote_count} votes)")
        print(f"Popularity: {movie.catalog_score}")
        print(f"TMDb ID: {movie.catalog_id}")
        print(f"Overview: {movie.overview}")

        if movie.poster and movie.poster.file_path:
            print(f"\nPoster URL: {movie.poster.file_path}")
        if movie.backdrop and movie.backdrop.file_path:
            print(f"Backdrop URL: {movie.backdrop.file_path}")

        if "videos" in movie.raw_data:
            video_count = len(movie.raw_data["videos"].get("results", []))
            print(f"Videos: {video_count} trailers/clips available")
        if "credits" in movie.raw_data:
            cast_count = len(movie.raw_data["credits"].get("cast", []))
            print(f"Credits: {cast_count} cast members")


async def test_search_with_filters():
    """Test search with various filters."""
    api_key = os.getenv("TMDB_API_KEY", "")
    access_token = os.getenv("TMDB_ACCESS_TOKEN", "")

    if not api_key and not access_token:
        print("⚠️  No TMDb credentials found. Set TMDB_API_KEY or TMDB_ACCESS_TOKEN")
        return

    async with TMDbClient(api_key=api_key, access_token=access_token) as client:
        print("\n🔍 Searching for 'Inception' (2010) with filters...")
        movies = await client.search_movie(
            "Inception", year=2010, language="en-US", limit=5
        )

        for movie in movies:
            print(f"- {movie.title} ({movie.year}) :: TMDb ID {movie.catalog_id}")


def main() -> None:
    asyncio.run(test_search_movie())
    asyncio.run(test_movie_details())
    asyncio.run(test_search_with_filters())


if __name__ == "__main__":
    main()
