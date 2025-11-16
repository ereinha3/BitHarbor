# TMDb API Client Documentation

## Overview

The TMDb (The Movie Database) API client provides a clean, modular interface for fetching movie metadata from TMDb's extensive database. This client follows TMDb API v3 specifications and supports both API key and Bearer token authentication.

## Features

- ✅ **Movie Search**: Search movies by title with optional year/region filters
- ✅ **Detailed Movie Info**: Fetch comprehensive movie metadata including genres, cast, crew, images, videos
- ✅ **Flexible Authentication**: Support for both API key and Bearer token (preferred)
- ✅ **Async/Await**: Fully asynchronous using httpx
- ✅ **Type Safety**: Complete type hints with dataclasses
- ✅ **Image URLs**: Helper methods to construct full image URLs
- ✅ **Append to Response**: Fetch additional data in a single request
- ✅ **Context Manager**: Safe resource management with async context manager
- ✅ **Error Handling**: Clear exception handling with detailed error messages

## Installation

The client requires `httpx` for HTTP requests. It's already included in the project dependencies.

## Configuration

### 1. Get TMDb API Credentials

Visit [TMDb API Settings](https://www.themoviedb.org/settings/api) to:
1. Register for a free API key
2. Get your API Read Access Token (Bearer token - recommended)

### 2. Configure in BitHarbor

Add TMDb credentials to your configuration:

**Environment Variables:**
```bash
export BITHARBOR_TMDB__API_KEY="your_api_key_here"
export BITHARBOR_TMDB__ACCESS_TOKEN="your_bearer_token_here"
```

**config.yaml:**
```yaml
tmdb:
  api_key: "your_api_key"
  access_token: "your_bearer_token"  # preferred
  language: "en-US"
  include_adult: false
```

## Usage Examples

### Basic Movie Search

```python
from api.tmdb import TMDbClient

async def search_movies():
    async with TMDbClient(
        api_key="your_key",
        access_token="your_token"  # optional, but preferred
    ) as client:
        # Search for movies
        results = await client.search_movie("The Matrix", year=1999)
        
        for movie in results:
            print(f"{movie.title} ({movie.release_date})")
            print(f"Rating: {movie.vote_average}/10")
            print(f"ID: {movie.id}")
```

### Get Detailed Movie Information

```python
async def get_movie_info():
    async with TMDbClient(access_token="your_token") as client:
        # Get full movie details
        movie = await client.get_movie_details(603)  # The Matrix
        
        print(f"Title: {movie.title}")
        print(f"Tagline: {movie.tagline}")
        print(f"Runtime: {movie.runtime} minutes")
        print(f"Budget: ${movie.budget:,}")
        print(f"Revenue: ${movie.revenue:,}")
        print(f"IMDb ID: {movie.imdb_id}")
        
        # Access genres
        for genre in movie.genres:
            print(f"Genre: {genre.name}")
        
        # Get image URLs
        poster_url = client.get_image_url(movie.poster_path, size="w500")
        backdrop_url = client.get_image_url(movie.backdrop_path, size="original")
```

### Advanced Search with Filters

```python
async def advanced_search():
    async with TMDbClient(access_token="your_token") as client:
        results = await client.search_movie(
            query="Inception",
            year=2010,
            language="en-US",
            region="US",
            page=1,
            include_adult=False
        )
        
        for movie in results:
            print(f"{movie.title} - Popularity: {movie.popularity}")
```

### Append Additional Data

```python
async def get_movie_with_extras():
    async with TMDbClient(access_token="your_token") as client:
        # Fetch movie details with videos and credits in one request
        movie = await client.get_movie_details(
            movie_id=603,
            append_to_response=["videos", "credits", "images", "reviews"]
        )
        
        # Access appended data from raw_data
        if "videos" in movie.raw_data:
            trailers = movie.raw_data["videos"]["results"]
            print(f"Found {len(trailers)} trailers")
        
        if "credits" in movie.raw_data:
            cast = movie.raw_data["credits"]["cast"][:5]
            for actor in cast:
                print(f"{actor['name']} as {actor['character']}")
```

### Integration with BitHarbor Settings

```python
from app.settings import get_settings
from api.tmdb import get_tmdb_client

async def use_with_settings():
    settings = get_settings()
    
    # Create client from settings
    client = get_tmdb_client(
        api_key=settings.tmdb.api_key,
        access_token=settings.tmdb.access_token
    )
    
    try:
        results = await client.search_movie(
            "Avatar",
            language=settings.tmdb.language,
            include_adult=settings.tmdb.include_adult
        )
        # Process results...
    finally:
        await client.close()
```

## API Reference

### TMDbClient

Main client class for TMDb API interactions.

**Constructor:**
```python
TMDbClient(api_key: str, access_token: Optional[str] = None)
```

**Methods:**

#### `search_movie()`
Search for movies by title.

```python
async def search_movie(
    query: str,
    *,
    year: Optional[int] = None,
    primary_release_year: Optional[int] = None,
    page: int = 1,
    include_adult: bool = False,
    region: Optional[str] = None,
    language: str = "en-US",
) -> list[TMDbSearchResult]
```

**Parameters:**
- `query`: Movie title to search for (required)
- `year`: Filter by release year
- `primary_release_year`: Filter by primary release year
- `page`: Page number (1-based)
- `include_adult`: Include adult content
- `region`: ISO 3166-1 country code
- `language`: Response language (e.g., "en-US", "es-ES")

**Returns:** List of `TMDbSearchResult` objects

#### `get_movie_details()`
Get detailed information about a specific movie.

```python
async def get_movie_details(
    movie_id: int,
    *,
    language: str = "en-US",
    append_to_response: Optional[list[str]] = None,
) -> TMDbMovie
```

**Parameters:**
- `movie_id`: TMDb movie ID (required)
- `language`: Response language
- `append_to_response`: Additional data to include (e.g., `["videos", "credits", "images"]`)

**Returns:** `TMDbMovie` object with detailed information

#### `get_image_url()`
Construct full image URL from TMDb image path.

```python
def get_image_url(
    path: Optional[str],
    size: str = "original"
) -> Optional[str]
```

**Parameters:**
- `path`: Image path from TMDb (e.g., from `poster_path` or `backdrop_path`)
- `size`: Image size
  - Poster sizes: `w92`, `w154`, `w185`, `w342`, `w500`, `w780`, `original`
  - Backdrop sizes: `w300`, `w780`, `w1280`, `original`

**Returns:** Full image URL or `None` if path is `None`

### Data Models

#### `TMDbSearchResult`
Represents a movie search result.

**Fields:**
- `id`: TMDb movie ID
- `title`: Movie title
- `original_title`: Original title (in original language)
- `release_date`: Release date (YYYY-MM-DD format)
- `overview`: Plot synopsis
- `poster_path`: Poster image path
- `backdrop_path`: Backdrop image path
- `popularity`: Popularity score
- `vote_average`: Average rating (0-10)
- `vote_count`: Number of votes
- `adult`: Adult content flag
- `original_language`: ISO 639-1 language code
- `genre_ids`: List of genre IDs

#### `TMDbMovie`
Represents detailed movie information.

**Fields:**
- All fields from `TMDbSearchResult`, plus:
- `tagline`: Movie tagline
- `runtime`: Runtime in minutes
- `status`: Release status
- `budget`: Production budget
- `revenue`: Box office revenue
- `homepage`: Official website URL
- `imdb_id`: IMDb identifier
- `genres`: List of `TMDbGenre` objects
- `production_companies`: List of `TMDbProductionCompany` objects
- `production_countries`: List of `TMDbProductionCountry` objects
- `spoken_languages`: List of `TMDbSpokenLanguage` objects
- `raw_data`: Complete raw API response (for additional fields)

## Error Handling

The client raises `TMDbAPIError` for API-related errors:

```python
from api.tmdb import TMDbClient, TMDbAPIError

async def handle_errors():
    async with TMDbClient(access_token="your_token") as client:
        try:
            results = await client.search_movie("Some Movie")
        except TMDbAPIError as e:
            print(f"API Error {e.status_code}: {e.message}")
            # Handle specific error codes
            if e.status_code == 401:
                print("Invalid API credentials")
            elif e.status_code == 404:
                print("Movie not found")
            elif e.status_code == 429:
                print("Rate limit exceeded")
```

## Best Practices

### 1. Use Bearer Token Authentication
Bearer tokens (API Read Access Token) are preferred over API keys:
```python
# Preferred
client = TMDbClient(access_token="your_bearer_token")

# Works but not preferred
client = TMDbClient(api_key="your_api_key")
```

### 2. Use Context Manager
Always use the async context manager to ensure proper cleanup:
```python
async with TMDbClient(access_token="token") as client:
    # Use client
    pass
# Client automatically closed
```

### 3. Leverage Append to Response
Reduce API calls by appending related data:
```python
# One API call instead of multiple
movie = await client.get_movie_details(
    movie_id,
    append_to_response=["videos", "credits", "images", "similar"]
)
```

### 4. Cache Movie IDs
After searching, cache the movie ID for future detail requests:
```python
# Search once
results = await client.search_movie("The Matrix", year=1999)
movie_id = results[0].id

# Use cached ID for details
movie = await client.get_movie_details(movie_id)
```

### 5. Handle Rate Limits
TMDb has rate limits (40 requests per 10 seconds). Implement retry logic:
```python
import asyncio
from api.tmdb import TMDbAPIError

async def search_with_retry(client, query, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.search_movie(query)
        except TMDbAPIError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

## Testing

Run the test suite:

```bash
# Set credentials
export TMDB_API_KEY="your_key"
export TMDB_ACCESS_TOKEN="your_token"

# Run tests
python tests/api/tmdb/test_client.py
```

## Integration Examples

### Use in Ingest Service

```python
from api.tmdb import get_tmdb_client
from app.settings import get_settings

async def enrich_movie_metadata(title: str, year: Optional[int] = None):
    settings = get_settings()
    
    async with get_tmdb_client(
        api_key=settings.tmdb.api_key,
        access_token=settings.tmdb.access_token
    ) as tmdb:
        # Search for the movie
        results = await tmdb.search_movie(title, year=year)
        
        if not results:
            return None
        
        # Get detailed info for best match
        movie = await tmdb.get_movie_details(
            results[0].id,
            append_to_response=["credits", "videos"]
        )
        
        # Convert to your metadata format
        return {
            "tmdb_id": movie.id,
            "imdb_id": movie.imdb_id,
            "title": movie.title,
            "original_title": movie.original_title,
            "year": movie.release_date[:4] if movie.release_date else None,
            "runtime_min": movie.runtime,
            "genres": [g.name for g in movie.genres],
            "overview": movie.overview,
            "tagline": movie.tagline,
            "poster_url": tmdb.get_image_url(movie.poster_path, "w500"),
            "backdrop_url": tmdb.get_image_url(movie.backdrop_path, "original"),
        }
```

### Use in Search Service

```python
async def smart_search_with_tmdb(query: str):
    """Combine vector search with TMDb metadata enrichment."""
    settings = get_settings()
    
    # Your existing vector search
    vector_results = await your_vector_search(query)
    
    # Enrich with TMDb data
    async with get_tmdb_client(
        access_token=settings.tmdb.access_token
    ) as tmdb:
        enriched_results = []
        
        for result in vector_results:
            if result.tmdb_id:
                # Fetch fresh metadata
                movie = await tmdb.get_movie_details(result.tmdb_id)
                result.metadata = {
                    "title": movie.title,
                    "rating": movie.vote_average,
                    "poster": tmdb.get_image_url(movie.poster_path, "w342"),
                }
            enriched_results.append(result)
        
        return enriched_results
```

## Resources

- [TMDb API Documentation](https://developer.themoviedb.org/docs)
- [TMDb API Reference](https://developer.themoviedb.org/reference)
- [Get API Key](https://www.themoviedb.org/settings/api)
- [TMDb Terms of Use](https://www.themoviedb.org/documentation/api/terms-of-use)

## License

This client implementation follows TMDb's API terms of use. Make sure to comply with their attribution requirements when displaying data.
