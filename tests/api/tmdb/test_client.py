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
        results = await client.search_movie("The Matrix", year=1999)

        print(f"Found {len(results)} results:\n")
        for i, movie in enumerate(results[:5], 1):
            print(f"{i}. {movie.title} ({movie.release_date})")
            print(f"   ID: {movie.id}")
            print(f"   Rating: {movie.vote_average}/10 ({movie.vote_count} votes)")
            print(f"   Overview: {movie.overview[:100]}...")
            if movie.poster_path:
                poster_url = client.get_image_url(movie.poster_path, size="w500")
                print(f"   Poster: {poster_url}")
            print()


async def test_movie_details():
    """Test fetching detailed movie information."""
    api_key = os.getenv("TMDB_API_KEY", "")
    access_token = os.getenv("TMDB_ACCESS_TOKEN", "")

    if not api_key and not access_token:
        print("⚠️  No TMDb credentials found. Set TMDB_API_KEY or TMDB_ACCESS_TOKEN")
        return

    async with TMDbClient(api_key=api_key, access_token=access_token) as client:
        # The Matrix (1999) - ID: 603
        movie_id = 603
        print(f"\n📽️  Fetching details for movie ID {movie_id}...")

        movie = await client.get_movie_details(
            movie_id, append_to_response=["videos", "credits"]
        )

        print(f"\nTitle: {movie.title}")
        print(f"Original Title: {movie.original_title}")
        print(f"Tagline: {movie.tagline}")
        print(f"Release Date: {movie.release_date}")
        print(f"Runtime: {movie.runtime} minutes")
        print(f"Status: {movie.status}")
        print(f"Budget: ${movie.budget:,}")
        print(f"Revenue: ${movie.revenue:,}")
        print(f"Rating: {movie.vote_average}/10 ({movie.vote_count} votes)")
        print(f"Popularity: {movie.popularity}")
        print(f"IMDb ID: {movie.imdb_id}")
        print(f"Homepage: {movie.homepage}")
        print(f"\nOverview:\n{movie.overview}")

        print(f"\nGenres: {', '.join(g.name for g in movie.genres)}")
        print(
            f"Languages: {', '.join(lang.english_name for lang in movie.spoken_languages)}"
        )
        print(
            f"Production Countries: {', '.join(c.name for c in movie.production_countries)}"
        )
        print(
            f"Production Companies: {', '.join(c.name for c in movie.production_companies[:3])}"
        )

        if movie.poster_path:
            print(f"\nPoster URL: {client.get_image_url(movie.poster_path)}")
        if movie.backdrop_path:
            print(f"Backdrop URL: {client.get_image_url(movie.backdrop_path)}")

        # Show appended data if present
        if "videos" in movie.raw_data:
            video_count = len(movie.raw_data["videos"].get("results", []))
            print(f"\nVideos: {video_count} trailers/clips available")

        if "credits" in movie.raw_data:
            cast_count = len(movie.raw_data["credits"].get("cast", []))
            crew_count = len(movie.raw_data["credits"].get("crew", []))
            print(f"Credits: {cast_count} cast members, {crew_count} crew members")


async def test_search_with_filters():
    """Test search with various filters."""
    api_key = os.getenv("TMDB_API_KEY", "")
    access_token = os.getenv("TMDB_ACCESS_TOKEN", "")

    if not api_key and not access_token:
        print("⚠️  No TMDb credentials found. Set TMDB_API_KEY or TMDB_ACCESS_TOKEN")
        return

    async with TMDbClient(api_key=api_key, access_token=access_token) as client:
        print("\n🔍 Searching for 'Inception' (2010) with filters...")
        results = await client.search_movie(
            "Inception", year=2010, language="en-US", page=1
        )

        if results:
            movie = results[0]
            print(f"\nTop Result:")
            print(f"Title: {movie.title}")
            print(f"Release Date: {movie.release_date}")
            print(f"Rating: {movie.vote_average}/10")
            print(f"Popularity: {movie.popularity}")
            print(f"Language: {movie.original_language}")


async def main():
    """Run all tests."""
    print("=" * 80)
    print("TMDb API Client Test Suite")
    print("=" * 80)

    await test_search_movie()
    await test_movie_details()
    await test_search_with_filters()

    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
