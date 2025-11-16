# Type-Specific API Routes Implementation

## Overview
Created type-specific router modules for each of the 6 media types in BitHarbor to provide dedicated endpoints for the frontend.

## Media Types
1. **movies** - Movie media library
2. **tv** - TV episodes/series library  
3. **music** - Music track library
4. **podcasts** - Podcast episode library
5. **videos** - Online video library
6. **personal** - Personal media library (photos, home videos)

## New Endpoint Structure

Each media type now has its own set of 5 endpoints:

### 1. Search
**Endpoint:** `POST /api/v1/{type}/search`
- Vector search across that specific media type
- Request body: `SearchRequest` with query and optional parameters
- Automatically filters results to only the specified media type

### 2. List Media
**Endpoint:** `GET /api/v1/{type}/media`
- List all media items of that type (paginated)
- Query params: `limit` (default: 20, max: 100), `offset` (default: 0)
- Returns: `MediaListResponse` with items and total count

### 3. Get Media Detail  
**Endpoint:** `GET /api/v1/{type}/media/{media_id}`
- Fetch detailed metadata for a specific media item
- Returns: `MediaDetail` with full metadata

### 4. Stream Media
**Endpoint:** `GET /api/v1/{type}/media/{media_id}/stream`
- Stream the original media file
- Returns: `FileResponse` with range request support

### 5. Ingest Media
**Endpoint:** `POST /api/v1/{type}/ingest/start`
- Ingest a new media file into that specific library
- Request body: `IngestRequest` (media_type is automatically set)
- Returns: `IngestResponse` with media_id, file_hash, and vector_hash

## Complete Endpoint List

### Movies
- `POST /api/v1/movies/search`
- `GET /api/v1/movies/media`
- `GET /api/v1/movies/media/{media_id}`
- `GET /api/v1/movies/media/{media_id}/stream`
- `POST /api/v1/movies/ingest/start`

### TV
- `POST /api/v1/tv/search`
- `GET /api/v1/tv/media`
- `GET /api/v1/tv/media/{media_id}`
- `GET /api/v1/tv/media/{media_id}/stream`
- `POST /api/v1/tv/ingest/start`

### Music
- `POST /api/v1/music/search`
- `GET /api/v1/music/media`
- `GET /api/v1/music/media/{media_id}`
- `GET /api/v1/music/media/{media_id}/stream`
- `POST /api/v1/music/ingest/start`

### Podcasts
- `POST /api/v1/podcasts/search`
- `GET /api/v1/podcasts/media`
- `GET /api/v1/podcasts/media/{media_id}`
- `GET /api/v1/podcasts/media/{media_id}/stream`
- `POST /api/v1/podcasts/ingest/start`

### Videos
- `POST /api/v1/videos/search`
- `GET /api/v1/videos/media`
- `GET /api/v1/videos/media/{media_id}`
- `GET /api/v1/videos/media/{media_id}/stream`
- `POST /api/v1/videos/ingest/start`

### Personal
- `POST /api/v1/personal/search`
- `GET /api/v1/personal/media`
- `GET /api/v1/personal/media/{media_id}`
- `GET /api/v1/personal/media/{media_id}/stream`
- `POST /api/v1/personal/ingest/start`

## Implementation Details

### File Structure
```
src/features/
├── movies/
│   ├── __init__.py
│   └── router.py
├── tv/
│   ├── __init__.py
│   └── router.py
├── music/
│   ├── __init__.py
│   └── router.py
├── podcasts/
│   ├── __init__.py
│   └── router.py
├── videos/
│   ├── __init__.py
│   └── router.py
└── personal/
    ├── __init__.py
    └── router.py
```

### Route Registration
All type-specific routers are registered in `src/api/v1/router.py` while maintaining backward compatibility with the original general-purpose endpoints.

### Key Features
- **Automatic Type Filtering**: Each router automatically sets/filters the media_type
- **Reuses Existing Services**: All routers leverage existing service layer (IngestService, MediaService, SearchService)
- **JWT Authentication**: All endpoints require valid admin token via `get_current_admin` dependency
- **Backward Compatible**: Original general-purpose endpoints remain available

### Original Endpoints (Still Available)
- `POST /api/v1/search` - General search across all types
- `GET /api/v1/media` - List all media (with optional type filter)
- `GET /api/v1/media/{media_id}` - Get any media detail
- `GET /api/v1/media/{media_id}/stream` - Stream any media
- `POST /api/v1/ingest/start` - General ingest (user specifies type)

## Frontend Integration
The bitharbor-web frontend can now make type-specific requests:

```typescript
// Example: Search movies
POST /api/v1/movies/search
{
  "query": "action movies from the 90s",
  "k": 20
}

// Example: List TV episodes
GET /api/v1/tv/media?limit=50&offset=0

// Example: Ingest personal photo
POST /api/v1/personal/ingest/start
{
  "path": "/path/to/photo.jpg",
  "metadata": {"album_name": "Vacation 2025"}
}
```

## Testing
Once dependencies are installed, test the API:
```bash
# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Check API docs
curl http://localhost:8080/docs
```

All endpoints will appear organized by their respective tags (movies, tv, music, podcasts, videos, personal) in the OpenAPI/Swagger documentation.
