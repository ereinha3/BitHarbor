# Metadata Enrichment Integration

## Overview

The metadata enrichment pipeline automatically fetches and integrates rich metadata from external sources (TMDb) during media ingestion. This enhances the BitHarbor database with comprehensive information about movies and TV shows.

## Architecture

### Components

1. **MetadataEnrichmentService** (`features/ingest/enrichment.py`)
   - Manages TMDb API client
   - Searches for media by title and year
   - Fetches detailed metadata with credits and images
   - Formats data for database storage

2. **IngestService** (`features/ingest/service.py`)
   - Main ingestion pipeline
   - Integrates enrichment service
   - Falls back to basic metadata if enrichment fails
   - Handles both enriched and non-enriched paths

### Flow

```
Ingest Request
    ↓
File Storage & Hashing
    ↓
Extract Basic Metadata
    ↓
┌─────────────────────────────┐
│ Media Type Check            │
├─────────────────────────────┤
│ • Movie → TMDb Enrichment   │
│ • TV → (Future)             │
│ • Personal → No Enrichment  │
│ • Other → No Enrichment     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ TMDb Enrichment (Movies)    │
├─────────────────────────────┤
│ 1. Search by title + year   │
│ 2. Get best match details   │
│ 3. Fetch credits & images   │
│ 4. Format for database      │
│ 5. Fallback if fails        │
└─────────────────────────────┘
    ↓
Create Media Record with:
• Rich metadata (if enriched)
• Cast and crew
• Posters and backdrops
• TMDb and IMDb IDs
• OR basic metadata (fallback)
    ↓
Generate Embeddings
    ↓
Add to ANN Index
    ↓
Return Success
```

## Enriched Data Fields

### Movies

When TMDb enrichment succeeds, the following fields are populated:

#### Core Fields
- `tmdb_id` - TMDb movie ID
- `imdb_id` - IMDb identifier
- `title` - Movie title
- `original_title` - Original title (in original language)
- `year` - Release year
- `release_date` - Full release date
- `runtime_min` - Runtime in minutes

#### Descriptive Fields
- `overview` - Plot synopsis
- `tagline` - Movie tagline
- `genres` - Pipe-separated genre names
- `languages` - Pipe-separated spoken languages
- `countries` - Pipe-separated production countries

#### People
- `cast_json` - Top 20 cast members with characters (JSON array)
- `crew_json` - Key crew (directors, writers, producers) (JSON array)

#### Images
- `posters_json` - Up to 10 poster images (JSON array)
- `backdrops_json` - Up to 10 backdrop images (JSON array)

#### Raw Data
- `metadata_raw` - Original user-provided metadata (JSON)
- `metadata_enriched` - Complete TMDb API response (JSON)

## Usage

### Basic Movie Ingestion

```bash
POST /api/v1/movies/ingest/start
{
  "path": "/path/to/movie.mp4",
  "media_type": "movie",
  "source_type": "catalog",
  "metadata": {
    "title": "The Matrix",
    "year": 1999
  }
}
```

**What Happens:**
1. File is stored and hashed
2. TMDb is searched for "The Matrix" (1999)
3. Best match details are fetched including:
   - Cast (Keanu Reeves, Laurence Fishburne, etc.)
   - Crew (Wachowski Brothers, etc.)
   - Posters and backdrops
   - Complete metadata (budget, revenue, ratings, etc.)
4. All data is stored in the database
5. Movie is indexed for vector search

### Fallback Behavior

If TMDb enrichment fails (no API key, not found, API error):

```python
# Enrichment fails gracefully
logger.warning("TMDb enrichment failed, using basic metadata")

# Basic metadata from request is still saved
Movie(
    title="The Matrix",
    year=1999,
    # ... other basic fields
)
```

## Configuration

### Required: TMDb Credentials

Set in environment or `config.yaml`:

```bash
# Environment variables
export BITHARBOR_TMDB__ACCESS_TOKEN="your_bearer_token"
# OR
export BITHARBOR_TMDB__API_KEY="your_api_key"

# Optional settings
export BITHARBOR_TMDB__LANGUAGE="en-US"
export BITHARBOR_TMDB__INCLUDE_ADULT="false"
```

```yaml
# config.yaml
tmdb:
  access_token: "your_bearer_token"  # preferred
  api_key: "your_api_key"
  language: "en-US"
  include_adult: false
```

### Get TMDb Credentials

1. Create free account at https://www.themoviedb.org
2. Go to https://www.themoviedb.org/settings/api
3. Get your **API Read Access Token** (Bearer token - recommended)

## Error Handling

The enrichment service handles errors gracefully:

### Scenario 1: No TMDb Credentials
```python
# Service logs warning but continues with basic metadata
logger.warning("TMDb credentials not configured")
# Falls back to user-provided metadata
```

### Scenario 2: Movie Not Found
```python
# Service logs warning
logger.warning("No TMDb results found for: Some Obscure Movie")
# Falls back to user-provided metadata
```

### Scenario 3: API Error
```python
# Service logs error
logger.error("Error during TMDb enrichment: Rate limit exceeded")
# Falls back to user-provided metadata
```

### Scenario 4: Partial Data
```python
# Service uses whatever data is available
# Missing fields are set to None/null in database
```

## Logging

The enrichment process provides detailed logging:

```
INFO: Searching TMDb for movie: The Matrix (1999)
INFO: Found TMDb match: The Matrix (ID: 603)
INFO: Successfully enriched movie: The Matrix (TMDb ID: 603, IMDb ID: tt0133093)
INFO: Using enriched TMDb metadata for movie: The Matrix
```

Or in case of failure:

```
WARNING: No TMDb results found for: Unknown Movie
WARNING: TMDb enrichment failed, using basic metadata for: Unknown Movie
```

## Database Schema

The enrichment integrates with existing `movies` table schema:

```sql
CREATE TABLE movies (
    media_id TEXT PRIMARY KEY,
    tmdb_id INTEGER,              -- ✨ Enriched
    imdb_id TEXT,                 -- ✨ Enriched
    title TEXT,                   -- ✨ Enriched or fallback
    original_title TEXT,          -- ✨ Enriched
    year INTEGER,                 -- ✨ Enriched or fallback
    release_date DATETIME,        -- ✨ Enriched
    runtime_min INTEGER,          -- ✨ Enriched
    genres TEXT,                  -- ✨ Enriched
    languages TEXT,               -- ✨ Enriched
    countries TEXT,               -- ✨ Enriched
    overview TEXT,                -- ✨ Enriched
    tagline TEXT,                 -- ✨ Enriched
    cast_json TEXT,               -- ✨ Enriched
    crew_json TEXT,               -- ✨ Enriched
    posters_json TEXT,            -- ✨ Enriched
    backdrops_json TEXT,          -- ✨ Enriched
    metadata_raw TEXT,            -- Original request
    metadata_enriched TEXT,       -- ✨ Complete TMDb response
    meta_fingerprint TEXT,
    ...
);
```

## Performance Considerations

### API Rate Limits
- TMDb: 40 requests per 10 seconds
- Consider implementing request queuing for batch ingests
- The service handles rate limit errors gracefully

### Async Processing
- Enrichment is fully asynchronous
- Does not block file storage or embedding generation
- Can be disabled by not providing TMDb credentials

### Caching
- Consider implementing caching layer for frequently searched movies
- TMDb data changes rarely, safe to cache for extended periods

## Future Enhancements

### TV Show Support
```python
# Planned implementation
async def enrich_tv_show(self, title: str, year: Optional[int]) -> dict:
    # Search TMDb TV API
    # Fetch series details
    # Handle episodes and seasons
    pass
```

### Additional Sources
- **OMDB API** for alternative movie data
- **MusicBrainz** for music metadata
- **Podcast Index** for podcast information
- **YouTube API** for online videos

### Smart Matching
- Fuzzy title matching
- Multi-source validation
- Confidence scoring
- Manual override capability

### Background Jobs
- Async task queue for batch enrichment
- Re-enrich existing media with updated data
- Periodic metadata refresh

## Testing

### Manual Test

```bash
# 1. Set credentials
export BITHARBOR_TMDB__ACCESS_TOKEN="your_token"

# 2. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# 3. Ingest a movie
curl -X POST http://localhost:8080/api/v1/movies/ingest/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/matrix.mp4",
    "media_type": "movie",
    "metadata": {
      "title": "The Matrix",
      "year": 1999
    }
  }'

# 4. Check logs for enrichment status
# 5. Query the movie to see enriched metadata
```

### Verify Enrichment

```python
# Get the movie details
response = requests.get(
    f"http://localhost:8080/api/v1/movies/media/{media_id}",
    headers={"Authorization": f"Bearer {token}"}
)

movie = response.json()

# Check enriched fields
assert movie["metadata"]["tmdb_id"] is not None
assert movie["metadata"]["imdb_id"] == "tt0133093"
assert movie["metadata"]["cast_json"] is not None
assert movie["metadata"]["overview"] is not None
```

## Troubleshooting

### Issue: "TMDb credentials not configured"
**Solution:** Set `BITHARBOR_TMDB__ACCESS_TOKEN` environment variable

### Issue: "No TMDb results found"
**Solution:** 
- Check title spelling
- Try with release year
- Verify movie exists on TMDb
- Check TMDb API is accessible

### Issue: Enrichment is slow
**Solution:**
- Normal for first request (TMDb API latency)
- Consider implementing caching
- Check network connectivity

### Issue: Missing some enriched fields
**Solution:**
- Some movies may have incomplete TMDb data
- Check `metadata_enriched` for raw TMDb response
- Some fields are optional in TMDb database

## Summary

✅ **Implemented**
- Automatic TMDb enrichment for movies during ingestion
- Rich metadata including cast, crew, images
- Graceful fallback to basic metadata
- Comprehensive error handling and logging
- Zero breaking changes to existing ingestion

🚧 **Coming Next**
- TV show enrichment
- Additional metadata sources
- Smart search integration
- Background re-enrichment jobs

The metadata enrichment is **production-ready** and enhances the ingestion pipeline without disrupting existing functionality!
