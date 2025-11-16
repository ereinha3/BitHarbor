# BitHarbor Repository Summary

**Last Updated:** November 16, 2025  
**Review Scope:** Complete repository analysis

---

## 🎯 Project Overview

**BitHarbor** is a local-first, AI-powered media server backend that provides multimodal search across personal media libraries using ImageBind embeddings and DiskANN vector indexing.

### Core Capabilities
- 🎬 **Multi-format Media Support**: Movies, TV shows, music, podcasts, online videos, personal media
- 🔍 **Vector Search**: ImageBind embeddings for semantic/multimodal search
- 📊 **Rich Metadata**: Automatic TMDb enrichment for movies and TV shows
- 🎯 **Content-Addressed Storage**: BLAKE3 hashing with deduplication
- ⚡ **Fast Retrieval**: DiskANN approximate nearest neighbor index
- 🔐 **Secure**: JWT authentication with admin/participant roles
- 📥 **Catalog Integration**: YouTube and Internet Archive download support

---

## 🆕 Major New Features

### 1. YouTube Integration (`api/youtube/`)

**Purpose:** Download and extract metadata from YouTube videos

**Capabilities:**
- Search YouTube with configurable result limits
- Fetch metadata without downloading (useful for enrichment)
- Download videos in various qualities/formats (MP4, MKV, etc.)
- Download audio-only (MP3, FLAC, etc.) with FFmpeg post-processing
- Configurable output templates and quality settings

**Implementation:**
```python
from api.youtube import YouTubeClient

client = YouTubeClient()

# Search
results = client.search("python tutorial", max_results=5)

# Download video
result = client.download_video(
    url="https://youtube.com/watch?v=abc123",
    destination=Path("/downloads"),
    quality="bestvideo+bestaudio/best",
    merge_format="mp4"
)

# Download audio only
result = client.download_audio(
    url="https://youtube.com/watch?v=abc123",
    destination=Path("/downloads"),
    audio_format="mp3",
    audio_bitrate="192"
)
```

**Key Files:**
- `api/youtube/client.py` - Main YouTubeClient implementation
- `api/youtube/__init__.py` - Exports and types
- `tests/api/youtube/test_youtube.py` - Comprehensive test suite

**Dependencies:**
- `yt-dlp` - YouTube downloader library
- `ffmpeg` - Required for video/audio processing

---

### 2. Internet Archive Integration (`api/internetarchive/`)

**Purpose:** Search and download movies from archive.org's vast catalog

**Capabilities:**
- Search movies with advanced filters and sorting
- Fetch detailed metadata (title, year, formats, etc.)
- Download complete movie bundles:
  - Video file (MP4, MKV, etc.)
  - Cover art/poster
  - Metadata XML
  - Subtitles (SRT, VTT)
- Configurable download strategies with retry logic
- Smart file selection (prefers original quality)

**Implementation:**
```python
from api.internetarchive import InternetArchiveClient

client = InternetArchiveClient()

# Search for movies
results = client.search_movies(
    "Fantastic Planet",
    rows=10,
    sorts=["downloads desc"],
    filters=["language:eng"]
)

# Download complete movie bundle
bundle = client.collect_movie_assets(
    identifier="fantastic-planet__1973",
    destination=Path("/downloads"),
    include_subtitles=True
)

# Access downloaded files
print(bundle.video_path)        # /downloads/.../film.mp4
print(bundle.cover_art_path)    # /downloads/.../poster.jpg
print(bundle.subtitle_paths)    # [/downloads/.../subs.srt]
```

**Key Files:**
- `api/internetarchive/client.py` - Main client with search/download
- `api/internetarchive/__init__.py` - Exports and data classes
- `tests/api/internetarchive/test_internetarchive.py` - Test suite
- `tmp_download.py` - Example usage script

**Authentication:**
- Optional: Set `INTERNET_ARCHIVE_EMAIL` and `INTERNET_ARCHIVE_PASSWORD` for full access
- Works without credentials for public domain content

**Use Cases:**
1. **Catalog enrichment**: Download public domain films
2. **Research**: Access historical media archives
3. **Backup**: Download personal uploads from archive.org
4. **Educational**: Build curated collections from archive.org

---

### 3. Spotify API Integration (`api/spotify/`)

**Purpose:** Enrich music and podcast metadata from Spotify

**Capabilities:**
- **Music:**
  - Search tracks, albums, artists
  - Get detailed track information (duration, ISRC, preview URLs)
  - Fetch audio features (danceability, energy, tempo, key, etc.)
  - Get album and artist details
- **Podcasts:**
  - Search shows and episodes
  - Get show metadata (publisher, languages, episode count)
  - Get episode details (duration, release date, descriptions)

**Authentication:** Client Credentials Flow (server-to-server)

**Implementation:**
```python
from api.spotify import SpotifyClient

client = SpotifyClient(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Search for a track
results = await client.search(
    query="The Less I Know The Better",
    types=["track"],
    limit=5
)

# Get track details
track = await client.get_track("track_id")

# Get audio features
features = await client.get_audio_features("track_id")
print(f"Tempo: {features.tempo} BPM")
print(f"Energy: {features.energy}")
print(f"Danceability: {features.danceability}")

# Search podcasts
shows = await client.search(
    query="tech podcast",
    types=["show"],
    limit=10
)
```

**Key Files:**
- `api/spotify/client.py` - Complete Spotify Web API client
- `api/spotify/__init__.py` - Exports

**Data Classes:**
- `SpotifyTrack` - Track metadata
- `SpotifyAlbum` - Album details
- `SpotifyArtist` - Artist information
- `SpotifyAudioFeatures` - Audio analysis (tempo, key, etc.)
- `SpotifyShow` - Podcast show metadata
- `SpotifyEpisode` - Podcast episode details

---

### 4. TMDb Enrichment System (`features/ingest/enrichment.py`)

**Purpose:** Automatically enrich movie and TV metadata during ingestion

**What Gets Enriched:**

**Movies:**
- TMDb & IMDb IDs
- Cast (top 20 actors with character names)
- Crew (directors, writers, producers)
- Posters & backdrops (up to 10 each with metadata)
- Genres, languages, countries
- Plot synopsis, tagline
- Release dates, runtime, budget, revenue
- Ratings and popularity scores
- Full poster/backdrop URLs

**TV Shows:**
- TMDb & IMDb IDs
- Series metadata (seasons, episodes, status)
- Cast and crew for entire series
- Episode-specific metadata (air dates, runtime)
- Networks, creators
- All images and ratings

**Flow:**
```
Ingest Request
    ↓
Basic File Processing
    ↓
Type Detection (movie/tv/music/etc)
    ↓
[IF MOVIE OR TV]
    ↓
TMDb Search (title + year)
    ↓
Fetch Full Details
    ↓
Parse & Structure Data
    ↓
Store Enriched Metadata
    ↓
[IF ENRICHMENT FAILS]
    ↓
Fallback to Basic Metadata
```

**Configuration:**
```bash
# Environment
export BITHARBOR_TMDB__ACCESS_TOKEN="your_token"
export BITHARBOR_TMDB__API_KEY="your_api_key"
export BITHARBOR_TMDB__LANGUAGE="en-US"
export BITHARBOR_TMDB__INCLUDE_ADULT="false"
```

**Key Features:**
- Graceful degradation (fails to basic metadata if TMDb unavailable)
- Type-safe Pydantic schemas (`domain/schemas/enrichment.py`)
- Stores both raw TMDb response and structured metadata
- Async processing doesn't block ingestion pipeline

**Database Storage:**
```sql
-- Enriched fields added to movies/tv_series tables
metadata_enriched TEXT  -- JSON with type-safe MovieMetadata/TvShowMetadata
cast_json TEXT          -- Array of cast members
crew_json TEXT          -- Array of crew members
posters_json TEXT       -- Array of poster images
backdrops_json TEXT     -- Array of backdrop images
```

---

### 5. Type-Specific API Routes

**Purpose:** Provide dedicated endpoints for each media type

**Endpoints:** (All under `/api/v1/`)

```
/movies/*       - Movie-specific operations
/tv/*           - TV show/episode operations
/music/*        - Music track operations
/podcasts/*     - Podcast episode operations
/videos/*       - Online video operations
/personal/*     - Personal media operations
```

**Each Type Has:**
1. `POST /{type}/search` - Vector search filtered to type
2. `GET /{type}/media` - List media of this type
3. `GET /{type}/media/{id}` - Get details with enriched metadata
4. `GET /{type}/media/{id}/stream` - Stream media file
5. `POST /{type}/ingest/start` - Ingest media of this type

**Backward Compatibility:**
- Original general routes (`/media`, `/search`, `/ingest`) still work
- Type-specific routes auto-filter by media type
- Same response formats across all endpoints

---

## 📁 Repository Structure

```
BitHarbor/
├── api/                           # External API clients
│   ├── internetarchive/          # ✨ NEW: Internet Archive integration
│   │   ├── client.py            # Search & download movies
│   │   └── __init__.py
│   ├── spotify/                  # ✨ NEW: Spotify API client
│   │   ├── client.py            # Music/podcast metadata
│   │   └── __init__.py
│   ├── tmdb/                     # TMDb API client
│   │   ├── client.py            # Movie/TV search & details
│   │   ├── service.py           # High-level TMDb service
│   │   └── __init__.py
│   └── youtube/                  # ✨ NEW: YouTube integration
│       ├── client.py            # Download & metadata
│       └── __init__.py
│
├── app/                          # Application core
│   ├── main.py                  # FastAPI application
│   ├── settings.py              # Configuration management
│   └── logging.py               # Logging setup
│
├── db/                           # Database layer
│   ├── base.py                  # SQLAlchemy base
│   ├── init.py                  # Database initialization
│   ├── session.py               # Session management
│   └── models/
│       └── media.py             # Media models (Movie, TvSeries, etc.)
│
├── domain/                       # Domain schemas
│   └── schemas/
│       ├── auth.py              # Authentication schemas
│       ├── enrichment.py        # ✨ ENHANCED: Enriched metadata types
│       ├── ingest.py            # Ingestion schemas
│       ├── media.py             # Media response schemas
│       ├── participant.py       # Participant schemas
│       └── search.py            # Search schemas
│
├── features/                     # Feature modules
│   ├── auth/                    # Authentication & authorization
│   ├── ingest/                  # ✨ ENHANCED: Media ingestion
│   │   ├── enrichment.py        # TMDb enrichment service
│   │   ├── metadata.py          # Metadata extraction
│   │   ├── service.py           # Main ingestion service
│   │   ├── router.py            # Ingestion endpoints
│   │   └── ENRICHMENT.md        # Enrichment documentation
│   ├── media/                   # Media CRUD operations
│   ├── search/                  # Vector search
│   ├── participants/            # Participant management
│   ├── movies/                  # ✨ NEW: Movie-specific routes
│   ├── tv/                      # ✨ NEW: TV-specific routes
│   ├── music/                   # ✨ NEW: Music-specific routes
│   ├── podcasts/                # ✨ NEW: Podcast-specific routes
│   ├── videos/                  # ✨ NEW: Video-specific routes
│   └── personal/                # ✨ NEW: Personal media routes
│
├── infrastructure/               # Infrastructure services
│   ├── ann/                     # DiskANN vector index
│   │   ├── diskann.py           # DiskANN bindings
│   │   ├── service.py           # ANN service
│   │   └── vector_store.py      # Vector storage
│   ├── embedding/               # Embedding generation
│   │   └── imagebind_service.py # ImageBind embeddings
│   └── storage/                 # File storage
│       └── content_addressable.py  # Content-addressed storage
│
├── router/                       # API routing
│   └── v1/
│       └── router.py            # ✨ ENHANCED: Main router with type routes
│
├── tests/                        # Test suite
│   ├── api/
│   │   ├── internetarchive/     # ✨ NEW: Internet Archive tests
│   │   ├── youtube/             # ✨ NEW: YouTube tests
│   │   └── tmdb/                # TMDb tests
│   ├── test_health.py
│   ├── test_tv_enrichment_typing.py
│   └── test_tv_enrichment_integration.py
│
├── utils/                        # Utilities
│   └── hashing.py               # BLAKE3 hashing
│
├── scripts/
│   └── bitharbor.service        # systemd service file
│
├── API_REFERENCE.md             # ✨ NEW: Complete API documentation
├── CHANGES.md                   # ✨ NEW: Change log
├── README.md                    # Project overview
├── config.example.yaml          # Example configuration
├── requirements.txt             # Python dependencies
└── tmp_download.py              # ✨ NEW: Example download script
```

---

## 🗄️ Database Schema

### Core Tables

**`media_core`** - Central media registry
- `media_id` (PK) - UUID
- `type` - movie|tv|music|podcast|video|personal
- `file_hash` - BLAKE3 hash of file
- `vector_hash` - Hash of embedding
- `source_type` - catalog|home
- `embedding_source` - text|content|text+image
- `hdd_path_id` - Foreign key to file_paths
- Timestamps: `created_at`, `updated_at`

**`file_paths`** - Deduplicated file storage
- `hdd_path_id` (PK)
- `file_hash` - Unique BLAKE3 hash
- `modality` - video|image|audio
- `abs_path` - Absolute path to stored file
- `size_bytes` - File size

### Type-Specific Tables

**`movies`**
- Rich TMDb metadata (title, year, runtime, budget, revenue)
- `tmdb_id`, `imdb_id`
- Genres, languages, countries (pipe-separated)
- `cast_json`, `crew_json` (JSON arrays)
- `posters_json`, `backdrops_json` (JSON arrays)
- `metadata_enriched` - Type-safe MovieMetadata JSON
- `metadata_raw` - Original user metadata

**`tv_series`**
- Series-level metadata
- `tmdb_id`, `imdb_id`
- Season/episode counts
- Air dates, status, networks
- Cast, crew, images (JSON)
- `metadata_enriched` - Type-safe TvShowMetadata JSON

**`tv_episodes`**
- Episode-specific data
- `series_id` - Foreign key to tv_series
- `season_number`, `episode_number`
- Episode name, overview, air date
- `metadata_enriched` - Type-safe TvEpisodeMetadata JSON

**`music_tracks`**
- Artist, album, track info
- Duration, genres
- Placeholder for Spotify enrichment

**`podcast_episodes`**
- Show name, episode details
- Duration, publication date
- Placeholder for Spotify enrichment

**`online_videos`**
- Platform, video ID
- Upload date, creator
- Placeholder for YouTube enrichment

**`personal_media`**
- Device info (make, model)
- Album name, orientation
- Persons (JSON array)

---

## 🔌 API Architecture

### Base URL: `/api/v1`

### Authentication
All endpoints (except `/auth/setup` and `/auth/login`) require JWT:
```
Authorization: Bearer <token>
```

### Endpoint Categories

**1. Authentication** (`/auth`)
- `POST /auth/setup` - Bootstrap admin account
- `POST /auth/login` - Authenticate and get token
- `GET /auth/me` - Get current admin info

**2. Participants** (`/admin/participants`, `/participants`)
- List, create, update, assign participants

**3. General Media** (`/media`)
- Works across all media types
- `GET /media` - List with optional type filter
- `GET /media/{id}` - Get details with enriched metadata
- `GET /media/{id}/stream` - Stream file (supports ranges)

**4. Type-Specific** (`/movies`, `/tv`, `/music`, `/podcasts`, `/videos`, `/personal`)
- Each has search, list, detail, stream, ingest endpoints
- Auto-filtered to media type
- Same response format as general endpoints

**5. Search** (`/search`)
- `POST /search` - Vector similarity search
- Multimodal: searches across text, images, videos
- Supports type filtering, pagination

**6. Ingest** (`/ingest`)
- `POST /ingest/start` - Ingest new media file
- Handles all media types
- Automatic enrichment for movies/TV
- Returns media_id, file_hash, vector_hash

---

## 🧪 Testing

### Test Coverage

**API Tests:**
- `tests/api/youtube/` - YouTube client tests
- `tests/api/internetarchive/` - Internet Archive tests
- `tests/api/tmdb/` - TMDb client tests

**Integration Tests:**
- `test_tv_enrichment_typing.py` - Type safety validation
- `test_tv_enrichment_integration.py` - End-to-end enrichment
- `test_health.py` - Health check endpoint

**Testing Strategy:**
- Mock external APIs (yt-dlp, internetarchive, httpx)
- Test happy paths and error handling
- Validate data transformations
- Ensure backward compatibility

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest tests/api/youtube/

# With coverage
pytest --cov=api --cov-report=html
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Server
BITHARBOR_SERVER__HOST=0.0.0.0
BITHARBOR_SERVER__PORT=8080
BITHARBOR_SERVER__DATA_ROOT=/var/lib/bitharbor
BITHARBOR_SERVER__POOL_ROOT=/mnt/pool

# Database
BITHARBOR_DB__URL=sqlite+aiosqlite:////var/lib/bitharbor/bitharbor.sqlite

# Security
BITHARBOR_SECURITY__SECRET_KEY=<generate-secure-key>
BITHARBOR_SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Embeddings
BITHARBOR_EMBEDDING__MODEL_NAME=imagebind_huge
BITHARBOR_EMBEDDING__DEVICE=cuda  # or cpu/auto
BITHARBOR_EMBEDDING__DIM=1024

# ANN Index
BITHARBOR_ANN__METRIC=cosine
BITHARBOR_ANN__GRAPH_DEGREE=64
BITHARBOR_ANN__COMPLEXITY=100

# TMDb Enrichment
BITHARBOR_TMDB__ACCESS_TOKEN=<your-token>
BITHARBOR_TMDB__LANGUAGE=en-US
BITHARBOR_TMDB__INCLUDE_ADULT=false

# Internet Archive (optional)
INTERNET_ARCHIVE_EMAIL=<your-email>
INTERNET_ARCHIVE_PASSWORD=<your-password>

# Spotify (for future enrichment)
SPOTIFY_CLIENT_ID=<your-client-id>
SPOTIFY_CLIENT_SECRET=<your-secret>
```

### YAML Config

Alternative to environment variables:
```yaml
# /etc/bitharbor/config.yaml
server:
  host: 0.0.0.0
  port: 8080
  data_root: /var/lib/bitharbor
  pool_root: /mnt/pool

tmdb:
  access_token: "your-token"
  language: "en-US"

# ... etc
```

---

## 🚀 Deployment

### Production Setup

1. **Install Dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. **Configure:**
```bash
sudo mkdir -p /etc/bitharbor
sudo cp config.example.yaml /etc/bitharbor/config.yaml
# Edit config with secure values
```

3. **Setup systemd:**
```bash
sudo cp scripts/bitharbor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bitharbor
```

4. **Check Status:**
```bash
sudo systemctl status bitharbor
curl http://localhost:8080/healthz
```

### Performance Tuning

**Embedding Generation:**
- Use GPU for ImageBind (20-50x faster)
- Adjust `video_frames` setting for speed/quality tradeoff

**ANN Index:**
- Increase `graph_degree` for better recall
- Adjust `complexity` for search speed/accuracy balance
- Monitor `search_memory_budget`

**Database:**
- SQLite in WAL mode (default)
- Consider PostgreSQL for high concurrency
- Regular VACUUM for performance

---

## 🔄 Typical Workflows

### 1. Ingest Movie with Enrichment

```bash
# 1. Upload file to server
scp matrix.mp4 server:/tmp/

# 2. Ingest via API
curl -X POST http://localhost:8080/api/v1/movies/ingest/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/tmp/matrix.mp4",
    "metadata": {
      "title": "The Matrix",
      "year": 1999
    }
  }'

# Response includes media_id
# Enrichment happens automatically in background
# Movie is immediately searchable
```

### 2. Download from Internet Archive

```python
from api.internetarchive import InternetArchiveClient
from pathlib import Path

client = InternetArchiveClient()

# Search
results = client.search_movies("Metropolis 1927", rows=5)

# Download complete bundle
bundle = client.collect_movie_assets(
    identifier=results[0].identifier,
    destination=Path("/downloads"),
    include_subtitles=True
)

# Now ingest the downloaded movie
# (can use bundle.video_path in ingest request)
```

### 3. Download from YouTube

```python
from api.youtube import YouTubeClient
from pathlib import Path

client = YouTubeClient()

# Search
results = client.search("documentary full", max_results=10)

# Download best quality
result = client.download_video(
    url=results[0].url,
    destination=Path("/downloads"),
    quality="bestvideo+bestaudio/best"
)

# Ingest the video
# (use result.filepaths[0] in ingest request)
```

### 4. Search Across Library

```bash
# Natural language search
curl -X POST http://localhost:8080/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sci-fi movie with robots",
    "types": ["movie"],
    "k": 20
  }'

# Returns ranked results with similarity scores
# Works across text descriptions and visual content
```

---

## 📊 Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM
- **Pydantic v2** - Data validation
- **SQLite** - Default database (WAL mode)

### AI/ML
- **ImageBind** - Multimodal embeddings (Meta Research)
- **PyTorch** - Deep learning framework
- **DiskANN** - Approximate nearest neighbors

### External APIs
- **TMDb** - Movie/TV metadata enrichment
- **Spotify** - Music/podcast metadata (ready)
- **YouTube** - Video downloads (yt-dlp)
- **Internet Archive** - Public domain content

### Storage
- **Content-Addressed** - BLAKE3 hashing
- **Deduplication** - Automatic by hash
- **Pool-based** - Configurable storage pools

### Security
- **JWT** - Token-based auth
- **BLAKE3** - Fast, cryptographic hashing
- **Bcrypt** - Password hashing

---

## 🎯 Use Cases

### 1. Personal Media Server
- Organize family photos/videos
- Search by description ("beach vacation 2020")
- Dedupe across devices
- Preserve metadata

### 2. Movie Collection Manager
- Auto-enrich with TMDb data
- Download public domain films from Internet Archive
- Rich search (cast, genre, plot)
- Stream to devices

### 3. Research Archive
- Index historical footage
- Multimodal search (text + visual)
- Organize by topic/era
- Download from archive.org

### 4. Content Curation
- Build themed collections
- Download YouTube documentaries
- Enrich with external metadata
- Semantic similarity search

### 5. Media Analysis
- Analyze personal media library
- Find similar content
- Track viewing patterns
- Organize by visual similarity

---

## 📝 Recent Changes Summary

### API Additions
✅ YouTube client for video downloads and metadata  
✅ Internet Archive client for movie search and downloads  
✅ Spotify client for music/podcast enrichment (ready to use)  
✅ Type-specific routes for all media types  

### Enrichment System
✅ Automatic TMDb enrichment for movies  
✅ TV show enrichment support  
✅ Type-safe Pydantic schemas  
✅ Graceful fallback on failure  
✅ Comprehensive enrichment documentation  

### Infrastructure
✅ Enhanced database schema for enriched metadata  
✅ Content-addressed storage with deduplication  
✅ DiskANN vector index integration  
✅ Async service architecture  

### Testing
✅ YouTube client tests  
✅ Internet Archive client tests  
✅ TV enrichment integration tests  
✅ Type safety validation tests  

### Documentation
✅ Complete API reference (API_REFERENCE.md)  
✅ Enrichment guide (features/ingest/ENRICHMENT.md)  
✅ Change log (CHANGES.md)  
✅ This summary document  

---

## 🚧 Roadmap / TODOs

### High Priority
- [ ] Implement music enrichment with Spotify API
- [ ] Implement podcast enrichment with Spotify API
- [ ] Per-episode TV enrichment (currently series-level only)
- [ ] YouTube metadata enrichment integration
- [ ] Background job queue for batch enrichment

### Medium Priority
- [ ] Re-enrichment endpoint (update existing media)
- [ ] Bulk ingest API
- [ ] Duplicate detection UI
- [ ] Advanced search filters (genre, year, cast, etc.)
- [ ] Thumbnail generation for videos

### Nice to Have
- [ ] MusicBrainz integration for music
- [ ] Podcast Index API integration
- [ ] OMDB as alternative movie source
- [ ] Multi-source validation/confidence scoring
- [ ] Admin dashboard UI
- [ ] Batch download from Internet Archive

---

## 💡 Key Insights

### What's Working Well
1. **Modular Architecture** - Clean separation between features
2. **Async Throughout** - No blocking operations
3. **Type Safety** - Pydantic ensures data integrity
4. **Graceful Degradation** - System works even if enrichment fails
5. **Content Addressing** - Automatic deduplication saves space
6. **Multimodal Search** - ImageBind provides powerful semantic search

### Technical Debt
1. **Settings management** - No Spotify settings yet in AppSettings
2. **Error handling** - Could use more specific exception types
3. **Caching** - No caching layer for external API calls
4. **Rate limiting** - No rate limit handling for TMDb/Spotify
5. **Transaction management** - Could be more explicit

### Performance Considerations
1. **Embedding generation** - Requires GPU for reasonable speed
2. **Large libraries** - Consider sharding ANN index
3. **API latency** - TMDb/Spotify calls add ~200-500ms to ingestion
4. **Database** - SQLite works well to ~100k items, then consider PostgreSQL

---

## 🎓 Getting Started Guide

### For Developers

1. **Clone and Setup:**
```bash
git clone https://github.com/ereinha3/BitHarbor.git
cd BitHarbor
python -m venv .venv3119
source .venv3119/bin/activate
pip install -e .
```

2. **Configure:**
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your TMDb token
export BITHARBOR_TMDB__ACCESS_TOKEN="your-token"
```

3. **Run:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

4. **First Use:**
- Visit http://localhost:8080/docs for Swagger UI
- Create admin via `/api/v1/auth/setup`
- Use token for authenticated requests
- Ingest first media file

### For Frontend Developers

- See `API_REFERENCE.md` for complete endpoint documentation
- All responses use Pydantic schemas (type-safe)
- TypeScript interfaces provided in documentation
- Use `/docs` endpoint for interactive API testing

---

## 📞 Support & Resources

- **Repository:** https://github.com/ereinha3/BitHarbor
- **API Docs:** http://localhost:8080/docs (when running)
- **TMDb API:** https://www.themoviedb.org/settings/api
- **ImageBind:** https://github.com/facebookresearch/ImageBind
- **yt-dlp:** https://github.com/yt-dlp/yt-dlp
- **Internet Archive:** https://archive.org/developers/

---

**End of Repository Summary**
