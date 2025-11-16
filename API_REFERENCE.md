# BitHarbor API Reference

**Version:** v1  
**Base URL:** `/api/v1`  
**Authentication:** Bearer token (JWT) required for all endpoints except `/auth/setup` and `/auth/login`

---

## Table of Contents

- [Authentication](#authentication)
- [Participants](#participants)
- [General Media](#general-media)
- [Movies](#movies)
- [TV Shows](#tv-shows)
- [Music](#music)
- [Podcasts](#podcasts)
- [Videos](#videos)
- [Personal Media](#personal-media)
- [Search](#search)
- [Ingest](#ingest)
- [Schemas](#schemas)

---

## Authentication

### POST `/api/v1/auth/setup`

Bootstrap the system with an initial admin account.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "securePassword123",
  "display_name": "Admin User",
  "participants": [
    {
      "handle": "john_viewer",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "viewer"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  },
  "participants": [
    {
      "participant_id": "uuid-here",
      "handle": "john_viewer",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "viewer",
      "preferences_json": null
    }
  ]
}
```

---

### POST `/api/v1/auth/login`

Authenticate and receive access token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  },
  "participants": []
}
```

---

### GET `/api/v1/auth/me`

Get current authenticated admin details.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  }
}
```

---

## Participants

### GET `/api/v1/admin/participants`

List all participants for the current admin.

**Response:** `200 OK`
```json
[
  {
    "participant_id": "uuid-here",
    "handle": "john_viewer",
    "display_name": "John Doe",
    "email": "john@example.com",
    "role": "viewer",
    "preferences_json": null
  }
]
```

---

### POST `/api/v1/admin/participants`

Create a new participant.

**Request:**
```json
{
  "handle": "jane_viewer",
  "display_name": "Jane Smith",
  "email": "jane@example.com",
  "role": "viewer",
  "preferences_json": null
}
```

**Response:** `201 Created`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Smith",
  "email": "jane@example.com",
  "role": "viewer",
  "preferences_json": null
}
```

---

### PATCH `/api/v1/admin/participants/{participant_id}`

Update participant details.

**Request:**
```json
{
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "admin",
  "preferences_json": "{\"theme\": \"dark\"}"
}
```

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "admin",
  "preferences_json": "{\"theme\": \"dark\"}"
}
```

---

### POST `/api/v1/admin/participants/{participant_id}/assign`

Assign a role to a participant.

**Request:**
```json
{
  "role": "editor"
}
```

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "editor",
  "preferences_json": null
}
```

---

### GET `/api/v1/participants/{participant_id}`

Get a specific participant's details.

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "editor",
  "preferences_json": null
}
```

---

## General Media

These endpoints work across all media types.

### GET `/api/v1/media`

List all media items with optional type filtering.

**Query Parameters:**
- `media_type` (optional): Filter by type (`movie`, `tv`, `music`, `podcast`, `video`, `personal`)
- `limit` (default: 20, max: 100): Number of items to return
- `offset` (default: 0): Pagination offset

**Response:** `200 OK`
```json
{
  "items": [
    {
      "media_id": "uuid-here",
      "type": "movie",
      "title": "The Matrix",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    },
    {
      "media_id": "uuid-here",
      "type": "tv",
      "title": "Breaking Bad - S01E01",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    }
  ],
  "total": 2
}
```

---

### GET `/api/v1/media/{media_id}`

Get detailed information about a specific media item.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "movie",
  "title": "The Matrix",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 8160,
    "format": "mp4",
    "codec": "h264"
  },
  "enriched_metadata": {
    "movie": {
      "tmdb_id": 603,
      "imdb_id": "tt0133093",
      "title": "The Matrix",
      "original_title": "The Matrix",
      "tagline": "Welcome to the Real World.",
      "overview": "Set in the 22nd century...",
      "release_date": "1999-03-31T00:00:00",
      "year": 1999,
      "runtime_min": 136,
      "genres": ["Action", "Science Fiction"],
      "vote_average": 8.2,
      "vote_count": 23000,
      "cast": [
        {
          "name": "Keanu Reeves",
          "character": "Neo",
          "order": 0,
          "profile_path": "/path.jpg"
        }
      ],
      "crew": [
        {
          "name": "Lana Wachowski",
          "job": "Director",
          "department": "Directing"
        }
      ],
      "poster_url": "https://image.tmdb.org/t/p/original/path.jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/original/path.jpg"
    }
  }
}
```

---

### GET `/api/v1/media/{media_id}/stream`

Stream the original media file.

**Response:** `200 OK`
- Returns a `FileResponse` with appropriate `Content-Type` header
- Supports range requests for streaming

---

### POST `/api/v1/search`

Search across all media types using vector similarity.

**Request:**
```json
{
  "query": "action movie with robots",
  "types": ["movie", "tv"],
  "k": 20
}
```

**Response:** `200 OK`
```json
{
  "results": [
    {
      "media_id": "uuid-here",
      "score": 0.92,
      "type": "movie",
      "title": "The Matrix",
      "preview_url": "/api/v1/media/uuid-here/stream"
    },
    {
      "media_id": "uuid-here",
      "score": 0.87,
      "type": "movie",
      "title": "Terminator 2",
      "preview_url": "/api/v1/media/uuid-here/stream"
    }
  ]
}
```

---

### POST `/api/v1/ingest/start`

Ingest a new media file into the library.

**Request:**
```json
{
  "path": "/mnt/media/movies/matrix.mp4",
  "media_type": "movie",
  "source_type": "catalog",
  "metadata": {
    "title": "The Matrix",
    "year": 1999
  },
  "poster_path": "/mnt/posters/matrix.jpg"
}
```

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "file_hash": "sha256-hash",
  "vector_hash": "embedding-hash"
}
```

---

## Movies

Type-specific endpoints for movies. All endpoints require authentication.

### POST `/api/v1/movies/search`

Vector search across movie library only.

**Request:**
```json
{
  "query": "sci-fi action with time travel",
  "k": 10
}
```

**Response:** `200 OK`
```json
{
  "results": [
    {
      "media_id": "uuid-here",
      "score": 0.94,
      "type": "movie",
      "title": "The Matrix",
      "preview_url": "/api/v1/media/uuid-here/stream"
    }
  ]
}
```

---

### GET `/api/v1/movies/media`

List all movie media items.

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "media_id": "uuid-here",
      "type": "movie",
      "title": "The Matrix",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/movies/media/{media_id}`

Get detailed movie metadata including TMDb enrichment.

**Response:** `200 OK` - Same format as general media detail with `enriched_metadata.movie` populated.

---

### GET `/api/v1/movies/media/{media_id}/stream`

Stream the movie file.

---

### POST `/api/v1/movies/ingest/start`

Ingest a movie file.

**Request:**
```json
{
  "path": "/mnt/media/movies/matrix.mp4",
  "metadata": {
    "title": "The Matrix",
    "year": 1999
  },
  "poster_path": "/mnt/posters/matrix.jpg"
}
```
*Note: `media_type` is automatically set to `"movie"`*

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "file_hash": "sha256-hash",
  "vector_hash": "embedding-hash"
}
```

---

## TV Shows

Type-specific endpoints for TV episodes.

### POST `/api/v1/tv/search`

Vector search across TV library only.

**Request:**
```json
{
  "query": "crime drama with meth",
  "k": 10
}
```

**Response:** `200 OK` - Same format as movie search with `type: "tv"`.

---

### GET `/api/v1/tv/media`

List all TV episode media items.

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "media_id": "uuid-here",
      "type": "tv",
      "title": "Breaking Bad - S01E01",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/tv/media/{media_id}`

Get detailed TV episode metadata including TMDb enrichment.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "tv",
  "title": "Breaking Bad - S01E01",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 2880,
    "format": "mp4"
  },
  "enriched_metadata": {
    "tv_show": {
      "tmdb_id": 1396,
      "imdb_id": "tt0903747",
      "name": "Breaking Bad",
      "overview": "A high school chemistry teacher...",
      "first_air_date": "2008-01-20T00:00:00",
      "number_of_seasons": 5,
      "number_of_episodes": 62,
      "genres": ["Drama", "Crime"],
      "vote_average": 9.0
    },
    "tv_episode": {
      "tmdb_id": 62085,
      "series_name": "Breaking Bad",
      "series_tmdb_id": 1396,
      "name": "Pilot",
      "season_number": 1,
      "episode_number": 1,
      "air_date": "2008-01-20T00:00:00",
      "runtime_min": 58,
      "vote_average": 8.2
    }
  }
}
```

---

### GET `/api/v1/tv/media/{media_id}/stream`

Stream the TV episode file.

---

### POST `/api/v1/tv/ingest/start`

Ingest a TV episode file.

**Request:**
```json
{
  "path": "/mnt/media/tv/breaking_bad_s01e01.mp4",
  "metadata": {
    "title": "Breaking Bad",
    "season": 1,
    "episode": 1
  }
}
```
*Note: `media_type` is automatically set to `"tv"`*

**Response:** `200 OK` - Same format as movie ingest.

---

## Music

Type-specific endpoints for music tracks.

### POST `/api/v1/music/search`

Vector search across music library only.

**Request:**
```json
{
  "query": "upbeat electronic dance",
  "k": 10
}
```

**Response:** `200 OK` - Same format as movie search with `type: "music"`.

---

### GET `/api/v1/music/media`

List all music track media items.

---

### GET `/api/v1/music/media/{media_id}`

Get detailed music track metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "music",
  "title": "Song Title - Artist Name",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 240,
    "format": "mp3",
    "bitrate": 320000
  },
  "enriched_metadata": {
    "music": {
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "track_number": 3,
      "year": 2020,
      "genres": ["Electronic", "Dance"]
    }
  }
}
```

---

### GET `/api/v1/music/media/{media_id}/stream`

Stream the music track file.

---

### POST `/api/v1/music/ingest/start`

Ingest a music track file.

**Request:**
```json
{
  "path": "/mnt/media/music/artist/album/track.mp3",
  "metadata": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name"
  }
}
```
*Note: `media_type` is automatically set to `"music"`*

---

## Podcasts

Type-specific endpoints for podcast episodes.

### POST `/api/v1/podcasts/search`

Vector search across podcast library only.

---

### GET `/api/v1/podcasts/media`

List all podcast episode media items.

---

### GET `/api/v1/podcasts/media/{media_id}`

Get detailed podcast episode metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "podcast",
  "title": "Episode Title - Show Name",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 3600,
    "format": "mp3"
  },
  "enriched_metadata": {
    "podcast": {
      "title": "Episode Title",
      "show_name": "Show Name",
      "description": "Episode description...",
      "pub_date": "2024-01-15T00:00:00",
      "duration_s": 3600
    }
  }
}
```

---

### GET `/api/v1/podcasts/media/{media_id}/stream`

Stream the podcast episode file.

---

### POST `/api/v1/podcasts/ingest/start`

Ingest a podcast episode file.

---

## Videos

Type-specific endpoints for online videos (YouTube, etc.).

### POST `/api/v1/videos/search`

Vector search across online video library only.

---

### GET `/api/v1/videos/media`

List all online video media items.

---

### GET `/api/v1/videos/media/{media_id}`

Get detailed online video metadata.

---

### GET `/api/v1/videos/media/{media_id}/stream`

Stream the online video file.

---

### POST `/api/v1/videos/ingest/start`

Ingest an online video file.

---

## Personal Media

Type-specific endpoints for personal/home videos.

### POST `/api/v1/personal/search`

Vector search across personal media library only.

---

### GET `/api/v1/personal/media`

List all personal media items.

---

### GET `/api/v1/personal/media/{media_id}`

Get detailed personal media metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "personal",
  "title": "Family Vacation 2024",
  "source_type": "home",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 1200,
    "format": "mp4",
    "created_at": "2024-07-15T00:00:00"
  },
  "enriched_metadata": null
}
```

---

### GET `/api/v1/personal/media/{media_id}/stream`

Stream the personal media file.

---

### POST `/api/v1/personal/ingest/start`

Ingest a personal media file.

**Request:**
```json
{
  "path": "/mnt/home_videos/vacation_2024.mp4",
  "source_type": "home",
  "metadata": {
    "title": "Family Vacation 2024"
  }
}
```
*Note: `media_type` is automatically set to `"personal"`*

---

## Schemas

### MediaType Enum

```typescript
type MediaType = "movie" | "tv" | "music" | "podcast" | "video" | "personal";
```

### SourceType Enum

```typescript
type SourceType = "catalog" | "home";
```

### MediaSummary

```typescript
interface MediaSummary {
  media_id: string;
  type: MediaType;
  title: string | null;
  source_type: SourceType;
  vector_hash: string;
}
```

### MediaDetail

```typescript
interface MediaDetail extends MediaSummary {
  file_hash: string;
  metadata: Record<string, any> | null;
  enriched_metadata: EnrichedMetadata | null;
}
```

### EnrichedMetadata

```typescript
interface EnrichedMetadata {
  movie?: MovieMetadata;
  tv_show?: TvShowMetadata;
  tv_episode?: TvEpisodeMetadata;
  music?: MusicTrackMetadata;
  podcast?: PodcastEpisodeMetadata;
}
```

### MovieMetadata

```typescript
interface MovieMetadata {
  tmdb_id: number | null;
  imdb_id: string | null;
  title: string;
  original_title: string | null;
  tagline: string | null;
  overview: string | null;
  release_date: string | null;  // ISO 8601
  year: number | null;
  status: string | null;
  runtime_min: number | null;
  budget: number | null;
  revenue: number | null;
  genres: string[] | null;
  languages: string[] | null;
  countries: string[] | null;
  vote_average: number | null;  // 0-10
  vote_count: number | null;
  popularity: number | null;
  cast: CastMember[] | null;
  crew: CrewMember[] | null;
  poster_path: string | null;
  backdrop_path: string | null;
  posters: ImageMetadata[] | null;
  backdrops: ImageMetadata[] | null;
  poster_url: string | null;
  backdrop_url: string | null;
  homepage: string | null;
  adult: boolean | null;
}
```

### TvShowMetadata

```typescript
interface TvShowMetadata {
  tmdb_id: number | null;
  imdb_id: string | null;
  tvmaze_id: number | null;
  name: string;
  original_name: string | null;
  tagline: string | null;
  overview: string | null;
  type: string | null;
  status: string | null;
  first_air_date: string | null;  // ISO 8601
  last_air_date: string | null;  // ISO 8601
  number_of_seasons: number | null;
  number_of_episodes: number | null;
  genres: string[] | null;
  languages: string[] | null;
  countries: string[] | null;
  vote_average: number | null;
  vote_count: number | null;
  popularity: number | null;
  cast: CastMember[] | null;
  crew: CrewMember[] | null;
  created_by: string[] | null;
  poster_path: string | null;
  backdrop_path: string | null;
  posters: ImageMetadata[] | null;
  backdrops: ImageMetadata[] | null;
  poster_url: string | null;
  backdrop_url: string | null;
  homepage: string | null;
  networks: string[] | null;
}
```

### TvEpisodeMetadata

```typescript
interface TvEpisodeMetadata {
  tmdb_id: number | null;
  imdb_id: string | null;
  tvmaze_id: number | null;
  series_name: string | null;
  series_tmdb_id: number | null;
  name: string;
  overview: string | null;
  season_number: number;
  episode_number: number;
  air_date: string | null;  // ISO 8601
  runtime_min: number | null;
  vote_average: number | null;
  vote_count: number | null;
  cast: CastMember[] | null;
  crew: CrewMember[] | null;
  still_path: string | null;
  still_url: string | null;
}
```

### MusicTrackMetadata

```typescript
interface MusicTrackMetadata {
  musicbrainz_id: string | null;
  isrc: string | null;
  title: string;
  artist: string | null;
  album: string | null;
  track_number: number | null;
  disc_number: number | null;
  duration_s: number | null;
  year: number | null;
  genres: string[] | null;
}
```

### PodcastEpisodeMetadata

```typescript
interface PodcastEpisodeMetadata {
  guid: string | null;
  title: string;
  show_name: string | null;
  description: string | null;
  pub_date: string | null;  // ISO 8601
  duration_s: number | null;
  image_url: string | null;
}
```

### CastMember

```typescript
interface CastMember {
  name: string;
  character: string;
  order: number;  // 0 = top billed
  profile_path: string | null;
}
```

### CrewMember

```typescript
interface CrewMember {
  name: string;
  job: string;  // "Director", "Writer", etc.
  department: string;  // "Directing", "Writing", etc.
}
```

### ImageMetadata

```typescript
interface ImageMetadata {
  file_path: string;
  width: number | null;
  height: number | null;
  aspect_ratio: number | null;
  vote_average: number | null;
  vote_count: number | null;
  iso_639_1: string | null;  // Language code
}
```

### SearchRequest

```typescript
interface SearchRequest {
  query: string;  // Minimum length: 1
  types?: MediaType[];  // Optional filter
  k?: number;  // Default: 20, Range: 1-100
}
```

### SearchResult

```typescript
interface SearchResult {
  media_id: string;
  score: number;  // Similarity score
  type: MediaType;
  title: string | null;
  preview_url: string | null;
}
```

### IngestRequest

```typescript
interface IngestRequest {
  path: string;  // Absolute path to media file
  media_type?: MediaType;  // Default: "personal"
  source_type?: SourceType;  // Default: "home"
  metadata?: Record<string, any>;  // Optional metadata hints
  poster_path?: string;  // Optional poster image path
}
```

### IngestResponse

```typescript
interface IngestResponse {
  media_id: string;  // UUID of created media
  file_hash: string;  // SHA-256 hash
  vector_hash: string;  // Embedding hash
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found

```json
{
  "detail": "Media not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Notes

1. **Authentication**: All endpoints except `/auth/setup` and `/auth/login` require a valid JWT token in the `Authorization` header.

2. **Pagination**: List endpoints support `limit` and `offset` query parameters for pagination.

3. **Enrichment**: Movie and TV content is automatically enriched with TMDb metadata during ingestion. Music and podcast enrichment is planned for future releases.

4. **Vector Search**: Search uses ImageBind embeddings for multimodal similarity search across text descriptions and visual content.

5. **Streaming**: Stream endpoints return `FileResponse` objects with appropriate `Content-Type` headers and support HTTP range requests for efficient streaming.

6. **Type-Specific Routes**: Each media type has its own set of routes under `/movies`, `/tv`, `/music`, `/podcasts`, `/videos`, and `/personal` for convenience. These are equivalent to using the general routes with appropriate filters.

7. **Backward Compatibility**: The original general-purpose endpoints (`/media`, `/search`, `/ingest`) remain available for backward compatibility and cross-type operations.
