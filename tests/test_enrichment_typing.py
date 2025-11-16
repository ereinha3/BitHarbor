"""Test type-safe enriched metadata functionality.

This script demonstrates how the type-safe Pydantic schemas work
for enriched metadata, ensuring the frontend receives consistent,
typed responses even with partial or missing data.
"""

import asyncio
import json
from datetime import datetime
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from domain.schemas.enrichment import (
    CastMember,
    CrewMember,
    EnrichedMetadata,
    ImageMetadata,
    MovieMetadata,
)


def test_movie_metadata_full():
    """Test MovieMetadata with complete data."""
    print("\n=== Test 1: Full Movie Metadata ===")
    
    metadata = MovieMetadata(
        tmdb_id=603,
        imdb_id="tt0133093",
        title="The Matrix",
        original_title="The Matrix",
        tagline="Welcome to the Real World.",
        overview="A computer hacker learns about the true nature of his reality...",
        release_date=datetime(1999, 3, 31),
        year=1999,
        runtime_min=136,
        genres=["Action", "Science Fiction"],
        languages=["English"],
        countries=["United States of America"],
        vote_average=8.2,
        vote_count=23000,
        cast=[
            CastMember(name="Keanu Reeves", character="Neo", order=0),
            CastMember(name="Laurence Fishburne", character="Morpheus", order=1),
            CastMember(name="Carrie-Anne Moss", character="Trinity", order=2),
        ],
        crew=[
            CrewMember(name="Lana Wachowski", job="Director", department="Directing"),
            CrewMember(name="Lilly Wachowski", job="Director", department="Directing"),
        ],
        posters=[
            ImageMetadata(
                file_path="/abc123.jpg",
                width=500,
                height=750,
                aspect_ratio=0.667,
                vote_average=8.5,
                vote_count=100,
            )
        ],
    )
    
    # Convert to JSON (what would be sent to frontend)
    json_data = metadata.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    # Parse back from JSON (what frontend would receive)
    parsed = MovieMetadata.model_validate_json(json_data)
    print(f"\n✓ Successfully parsed! Title: {parsed.title}")
    print(f"✓ Cast count: {len(parsed.cast or [])}")
    print(f"✓ Genres: {', '.join(parsed.genres or [])}")


def test_movie_metadata_partial():
    """Test MovieMetadata with partial/missing data (common for failed enrichment)."""
    print("\n=== Test 2: Partial Movie Metadata ===")
    
    # Minimal required data (only title is required)
    metadata = MovieMetadata(
        title="Unknown Movie",
        # Everything else is None/optional
    )
    
    json_data = metadata.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    # Frontend can safely access optional fields
    parsed = MovieMetadata.model_validate_json(json_data)
    print(f"\n✓ Title (required): {parsed.title}")
    print(f"✓ Year (optional): {parsed.year}")  # None
    print(f"✓ Cast (optional): {parsed.cast}")  # None
    print(f"✓ Genres (optional): {parsed.genres}")  # None
    
    # Frontend can safely check for None
    if parsed.cast:
        print(f"Has {len(parsed.cast)} cast members")
    else:
        print("✓ No cast data available (gracefully handled)")


def test_enriched_metadata_container():
    """Test EnrichedMetadata container for different media types."""
    print("\n=== Test 3: EnrichedMetadata Container ===")
    
    # Movie metadata in container
    movie_metadata = MovieMetadata(
        title="Inception",
        year=2010,
        genres=["Action", "Sci-Fi", "Thriller"],
    )
    
    enriched = EnrichedMetadata(movie=movie_metadata)
    json_data = enriched.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    parsed = EnrichedMetadata.model_validate_json(json_data)
    
    # Frontend can check which type of metadata exists
    if parsed.movie:
        print(f"\n✓ Movie metadata present: {parsed.movie.title}")
    if parsed.tv_show:
        print("✓ TV show metadata present")
    else:
        print("✓ No TV show metadata (expected)")


def test_json_field_parsing():
    """Test parsing metadata_enriched from database JSON field."""
    print("\n=== Test 4: Database JSON Field Parsing ===")
    
    # Simulate what's stored in database
    movie_dict = {
        "tmdb_id": 27205,
        "title": "Inception",
        "year": 2010,
        "runtime_min": 148,
        "genres": ["Action", "Science Fiction", "Thriller"],
        "cast": [
            {"name": "Leonardo DiCaprio", "character": "Cobb", "order": 0},
            {"name": "Joseph Gordon-Levitt", "character": "Arthur", "order": 1},
        ],
        "vote_average": 8.4,
        "vote_count": 32000,
    }
    
    # Store as JSON (what database does)
    json_str = json.dumps(movie_dict)
    print(f"Database JSON: {json_str}")
    
    # Parse and validate (what media service does)
    parsed = MovieMetadata.model_validate_json(json_str)
    print(f"\n✓ Parsed from database JSON!")
    print(f"✓ Title: {parsed.title}")
    print(f"✓ Year: {parsed.year}")
    print(f"✓ Cast[0]: {parsed.cast[0].name} as {parsed.cast[0].character}")
    print(f"✓ Genres: {', '.join(parsed.genres)}")
    
    # Frontend receives type-safe data
    enriched = EnrichedMetadata(movie=parsed)
    frontend_json = enriched.model_dump_json(indent=2)
    print(f"\nFrontend receives:\n{frontend_json}")


def test_validation_error():
    """Test that invalid data is caught by Pydantic validation."""
    print("\n=== Test 5: Validation Error Handling ===")
    
    try:
        # Missing required field (title)
        MovieMetadata(
            year=2020,
            genres=["Action"],
        )
        print("✗ Should have raised validation error!")
    except Exception as e:
        print(f"✓ Validation error caught: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Type-Safe Enriched Metadata")
    print("=" * 60)
    
    test_movie_metadata_full()
    test_movie_metadata_partial()
    test_enriched_metadata_container()
    test_json_field_parsing()
    test_validation_error()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nKey Benefits:")
    print("✓ Frontend knows exactly what fields exist")
    print("✓ All fields (except title) are Optional")
    print("✓ Partial enrichment data handled gracefully")
    print("✓ Type validation ensures consistency")
    print("✓ Auto-generated API documentation shows schema")
    print("=" * 60)
