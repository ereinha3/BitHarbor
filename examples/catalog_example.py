#!/usr/bin/env python3
"""Example script demonstrating Internet Archive catalog integration.

This script shows how to:
1. Search Internet Archive for movies
2. Download and ingest a movie in one API call
3. Query the enriched movie metadata

Usage:
    python examples/catalog_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from features.catalog.service import CatalogService
from features.media.service import MediaService


async def search_example():
    """Example: Search Internet Archive for movies."""
    print("\n=== Searching Internet Archive ===")

    from api.catalog.internetarchive import InternetArchiveClient, MovieSearchOptions

    client = InternetArchiveClient()

    # Search for classic sci-fi films
    results = client.search_movies(
            title="Metropolis",
        options=MovieSearchOptions(
            limit=5,
            sorts=["downloads desc"],
            filters=["language:eng"],
            include_metadata=True,
        ),
    )

    print(f"\nFound {len(results)} results for 'Metropolis':\n")

    for i, result in enumerate(results, 1):
        metadata = result.metadata.get("item_metadata", {}).get("metadata", {})
        year = metadata.get("year", "Unknown")
        downloads = result.downloads or 0

        print(f"{i}. {result.title} ({year})")
        print(f"   Identifier: {result.identifier}")
        print(f"   Downloads: {downloads:,}")
        print()


async def download_and_ingest_example():
    """Example: Download and ingest a movie from Internet Archive."""
    print("\n=== Download and Ingest Movie ===")

    # Setup database connection
    engine = create_async_engine(
        "sqlite+aiosqlite:////var/lib/bitharbor/bitharbor.sqlite",
        echo=False,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        catalog_service = CatalogService()

        # Example: Download and ingest "Night of the Living Dead" (1968)
        # This is a public domain classic horror film
        identifier = "night_of_the_living_dead"

        print(f"Downloading and ingesting: {identifier}")
        print("This will:")
        print("  1. Download video, poster, and metadata from archive.org")
        print("  2. Extract Internet Archive metadata")
        print("  3. Enrich with TMDb (cast, crew, ratings)")
        print("  4. Generate ImageBind embeddings")
        print("  5. Add to search index")
        print("  6. Clean up downloaded files\n")

        try:
            result = await catalog_service.ingest_from_internet_archive(
                session=session,
                identifier=identifier,
                download_dir=Path("/tmp/bitharbor-downloads"),
                source_type="catalog",
                cleanup_after_ingest=True,
                include_subtitles=True,
            )

            print(f"\n✓ Success!")
            print(f"  Media ID: {result.media_id}")
            print(f"  File Hash: {result.file_hash}")
            print(f"  Vector Hash: {result.vector_hash}")

            # Fetch the ingested movie details
            media_service = MediaService()
            movie_detail = await media_service.get_media_detail(session, result.media_id)

            print(f"\n=== Movie Details ===")
            print(f"Title: {movie_detail.metadata.get('title', 'Unknown')}")
            print(f"Type: {movie_detail.type}")
            print(f"Source: {movie_detail.source_type}")

            if movie_detail.enriched_metadata and movie_detail.enriched_metadata.movie:
                movie = movie_detail.enriched_metadata.movie
                print(f"\n=== TMDb Enrichment ===")
                print(f"TMDb ID: {movie.tmdb_id}")
                print(f"IMDb ID: {movie.imdb_id}")
                print(f"Year: {movie.year}")
                print(f"Runtime: {movie.runtime_min} minutes")
                print(f"Rating: {movie.vote_average}/10 ({movie.vote_count} votes)")
                print(f"Genres: {', '.join(movie.genres) if movie.genres else 'N/A'}")

                if movie.cast:
                    print(f"\nTop Cast:")
                    for actor in movie.cast[:5]:
                        print(f"  • {actor.name} as {actor.character}")

                if movie.crew:
                    directors = [c for c in movie.crew if c.job == "Director"]
                    if directors:
                        print(f"\nDirector(s):")
                        for director in directors:
                            print(f"  • {director.name}")

            return result.media_id

        except Exception as e:
            print(f"\n✗ Error: {e}")
            raise


async def search_ingested_movie_example(media_id: str):
    """Example: Search for the ingested movie using vector search."""
    print("\n=== Vector Search ===")

    engine = create_async_engine(
        "sqlite+aiosqlite:////var/lib/bitharbor/bitharbor.sqlite",
        echo=False,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from features.search.service import SearchService
        from domain.schemas import SearchRequest

        search_service = SearchService()

        # Search for the movie using natural language
        query = "classic horror movie with zombies"
        print(f"Searching for: '{query}'\n")

        search_request = SearchRequest(
            query=query,
            types=["movie"],
            k=5,
        )

        results = await search_service.search(session, search_request)

        print(f"Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title} (Score: {result.score:.3f})")
            print(f"   Media ID: {result.media_id}")
            print(f"   Type: {result.type}")

            if result.media_id == media_id:
                print("   ★ This is the movie we just ingested!")

            print()


async def main():
    """Run all examples."""
    print("=" * 70)
    print("BitHarbor Catalog Integration Examples")
    print("=" * 70)

    try:
        # Example 1: Search Internet Archive
        await search_example()

        # Example 2: Download and ingest a movie
        # NOTE: This requires TMDb credentials and will actually ingest the movie
        # Comment out if you don't want to ingest
        # media_id = await download_and_ingest_example()

        # Example 3: Search for the ingested movie
        # await search_ingested_movie_example(media_id)

        print("\n" + "=" * 70)
        print("Examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run only the search example by default
    # Uncomment the full main() to run all examples including ingestion
    asyncio.run(search_example())
    # asyncio.run(main())
