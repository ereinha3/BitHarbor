# Internet Archive + Ingestion Pipeline Integration Plan

## Current State Analysis

### Internet Archive Download Feature

**Location:** `api/internetarchive/client.py`

**Key Method:** `collect_movie_assets()`

**What it does:**
1. Takes an Internet Archive identifier (e.g., "fantastic-planet__1973")
2. Fetches metadata from archive.org
3. Selects best files to download:
   - Video file (prefers `.mp4` with `source="original"`)
   - Cover art/poster (Item Tile or Thumbnail format)
   - Metadata XML (`_meta.xml`)
   - Subtitles (`.srt`, `.vtt`)
4. Downloads all files to a destination directory
5. Returns a `MovieAssetBundle` with local paths:
   ```python
   MovieAssetBundle(
       identifier="fantastic-planet__1973",
       title="Fantastic Planet",
       metadata={...},  # Full IA metadata
       video_path=Path("/downloads/fantastic-planet__1973/film.mp4"),
       cover_art_path=Path("/downloads/fantastic-planet__1973/poster.jpg"),
       metadata_xml_path=Path("/downloads/fantastic-planet__1973/_meta.xml"),
       subtitle_paths=[Path("/downloads/fantastic-planet__1973/subs.srt")]
   )
   ```

**Current Usage:** Standalone download (see `tmp_download.py`)

---

### Movie Ingestion Pipeline

**Location:** `features/ingest/service.py`

**Key Method:** `ingest(session, IngestRequest)`

**What it does:**

1. **File Processing:**
   - Validates source file exists
   - Detects modality (video/audio/image) from extension
   - Computes BLAKE3 file hash
   - Stores file in content-addressed storage (deduplication)

2. **Metadata Processing:**
   - Extracts metadata from `IngestRequest.metadata`
   - Builds text blob for embedding (title, description, etc.)
   - Computes metadata fingerprint
   - Serializes metadata to JSON

3. **Embedding Generation:**
   - For catalog media (movies): Uses text blob + optional poster image
   - For personal media: Uses video content directly
   - Generates ImageBind embedding (1024-dim vector)
   - Computes vector hash

4. **Database Storage:**
   - Creates `MediaCore` record (central registry)
   - Creates `FilePath` record (deduplication)
   - Creates type-specific record (e.g., `Movie`)

5. **TMDb Enrichment** (for movies):
   - Searches TMDb by title + year
   - Fetches detailed metadata:
     - Cast (top 20 actors with character names)
     - Crew (directors, writers, producers)
     - Posters & backdrops (up to 10 each)
     - Genres, languages, countries
     - Plot synopsis, tagline, ratings
     - TMDb ID, IMDb ID
   - Stores enriched metadata in `metadata_enriched` field
   - Falls back to basic metadata if enrichment fails

6. **Vector Index:**
   - Adds embedding to DiskANN index
   - Enables semantic search

7. **Commit:**
   - Commits all changes to database
   - Returns `IngestResponse` with media_id, file_hash, vector_hash

**Required Input:**
```python
IngestRequest(
    path="/path/to/video.mp4",      # Required: local file path
    media_type="movie",              # Required: movie|tv|music|podcast|video|personal
    source_type="catalog",           # Required: catalog|home
    metadata={                       # Optional: metadata hints
        "title": "Fantastic Planet",
        "year": 1973
    },
    poster_path="/path/to/poster.jpg"  # Optional: for better embeddings
)
```

---

## Integration Strategy

### Goal
Seamlessly download movies from Internet Archive and ingest them into BitHarbor with full enrichment.

### Integration Points

#### Option 1: High-Level Service (Recommended)
Create a new service that orchestrates both operations:

```python
# features/catalog/service.py

class CatalogService:
    """Service for acquiring media from external catalogs."""
    
    async def ingest_from_internet_archive(
        self,
        session: AsyncSession,
        identifier: str,
        *,
        download_dir: Path,
        source_type: str = "catalog"
    ) -> IngestResponse:
        """Download and ingest a movie from Internet Archive.
        
        Args:
            session: Database session
            identifier: Internet Archive identifier
            download_dir: Temporary directory for downloads
            source_type: catalog or home
            
        Returns:
            IngestResponse with media_id, file_hash, vector_hash
        """
        # 1. Download from Internet Archive
        ia_client = InternetArchiveClient()
        bundle = ia_client.collect_movie_assets(
            identifier=identifier,
            destination=download_dir,
            include_subtitles=True
        )
        
        # 2. Extract metadata from Internet Archive
        ia_metadata = self._extract_ia_metadata(bundle)
        
        # 3. Ingest the video file
        ingest_request = IngestRequest(
            path=str(bundle.video_path),
            media_type="movie",
            source_type=source_type,
            metadata=ia_metadata,
            poster_path=str(bundle.cover_art_path) if bundle.cover_art_path else None
        )
        
        ingest_service = IngestService()
        result = await ingest_service.ingest(session, ingest_request)
        
        # 4. Optional: Store IA-specific metadata
        # Could add ia_identifier to Movie table or separate table
        
        return result
```

#### Option 2: Low-Level Integration
Modify `IngestService` to handle Internet Archive identifiers directly:

```python
# In IngestRequest schema, add optional field:
ia_identifier: Optional[str] = None

# In IngestService.ingest(), check if ia_identifier is set:
if payload.ia_identifier:
    # Download from IA first, then continue with normal ingestion
    bundle = self._download_from_ia(payload.ia_identifier)
    source_path = bundle.video_path
    # Use bundle metadata to enhance payload.metadata
else:
    source_path = Path(payload.path)
```

---

## Recommended Implementation: Option 1

### Why Option 1 is Better:
1. **Separation of Concerns:** Catalog acquisition vs. file ingestion
2. **Testability:** Can test download and ingestion independently
3. **Extensibility:** Easy to add YouTube, other sources later
4. **Clarity:** Clear distinction between "download from catalog" and "ingest local file"
5. **Flexibility:** Can download without ingesting, or ingest existing downloads

### Architecture:
```
User Request
    ↓
CatalogRouter (new)
    ↓
CatalogService.ingest_from_internet_archive()
    ↓
┌─────────────────────────────┐
│ 1. InternetArchiveClient    │
│    - Search & download       │
│    - Get metadata            │
│    - Return MovieAssetBundle │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 2. Metadata Extraction       │
│    - Parse IA metadata       │
│    - Extract title, year     │
│    - Build IngestRequest     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 3. IngestService             │
│    - Store file              │
│    - Generate embeddings     │
│    - TMDb enrichment         │
│    - Save to database        │
│    - Add to vector index     │
└─────────────────────────────┘
    ↓
Return IngestResponse
```

---

## Implementation Steps

### Step 1: Create Catalog Service
**File:** `features/catalog/service.py`
- `CatalogService` class
- `ingest_from_internet_archive()` method
- `_extract_ia_metadata()` helper
- Error handling for download failures

### Step 2: Add API Endpoint
**File:** `features/catalog/router.py`
- `POST /api/v1/catalog/ingest/internet-archive`
- Request schema with identifier
- Response: Standard IngestResponse

### Step 3: Update Router
**File:** `router/v1/router.py`
- Register catalog router

### Step 4: Add Schemas
**File:** `domain/schemas/catalog.py`
- `InternetArchiveIngestRequest`
- Optional: `CatalogSource` enum

### Step 5: Handle Cleanup
- Decide: Keep or delete downloaded files after ingestion?
- Option A: Delete (save space)
- Option B: Keep (preserve originals, faster re-ingest)
- Option C: Configurable

### Step 6: Testing
- Unit tests for metadata extraction
- Integration tests for full pipeline
- Mock InternetArchiveClient in tests

---

## Metadata Mapping

### Internet Archive → IngestRequest

Internet Archive provides rich metadata:
```python
{
    "metadata": {
        "identifier": "fantastic-planet__1973",
        "title": "Fantastic Planet",
        "year": "1973",
        "description": "Animated science fiction film...",
        "creator": "René Laloux",
        "language": "eng",
        "runtime": "72:00",
        # ... many more fields
    }
}
```

Map to IngestRequest.metadata:
```python
{
    "title": "Fantastic Planet",
    "year": 1973,
    "overview": "Animated science fiction film...",
    "director": "René Laloux",
    "runtime_min": 72,
    "languages": ["English"],
    # These will be enhanced by TMDb enrichment
}
```

### TMDb Will Add:
- Cast and crew (from TMDb database)
- Accurate ratings
- Posters and backdrops
- Genres
- TMDb ID, IMDb ID
- Budget, revenue (if available)

---

## Edge Cases to Handle

1. **Movie Not Found on TMDb:**
   - Ingestion still succeeds with IA metadata
   - Movie stored with basic info
   - User can manually re-enrich later

2. **Download Fails:**
   - Return clear error to user
   - Don't leave partial files
   - Log for debugging

3. **File Already Exists (by hash):**
   - Ingestion pipeline already handles this
   - Returns existing media_id
   - Updates metadata if needed

4. **Disk Space:**
   - Check available space before download
   - Clean up on error
   - Make cleanup configurable

5. **Multiple Video Files:**
   - IA client already selects best file
   - Prefers "original" source
   - Prefers .mp4 format

---

## Example Usage

### API Request:
```bash
POST /api/v1/catalog/ingest/internet-archive
{
  "identifier": "fantastic-planet__1973",
  "download_dir": "/tmp/bitharbor-downloads",
  "source_type": "catalog",
  "cleanup_after_ingest": true
}
```

### What Happens:
1. Download video, poster, subtitles from archive.org
2. Extract title="Fantastic Planet", year=1973 from IA metadata
3. Ingest video with IA metadata
4. TMDb enriches with cast, crew, ratings, posters
5. Generate ImageBind embedding from text + IA poster
6. Add to DiskANN index
7. Delete downloaded files (if cleanup=true)
8. Return media_id

### Result:
- Movie is searchable: "sci-fi animation about tiny humans"
- Full metadata: TMDb cast, crew, plot
- Poster from archive.org used for embedding
- Original video stored in content-addressed storage
- Subtitles available (if downloaded separately)

---

## Benefits of This Integration

1. **One-Click Acquisition:** Download + ingest in single API call
2. **Full Enrichment:** IA metadata + TMDb enrichment
3. **Better Embeddings:** Uses IA poster for visual component
4. **Deduplication:** If movie already exists, reuses storage
5. **Searchable:** Immediately available in vector search
6. **Metadata Rich:** Combines IA, TMDb, and user metadata
7. **Extensible:** Easy to add YouTube, other catalogs

---

## Next: Let's Implement!

Ready to start coding? We'll build:
1. `features/catalog/service.py` - Core integration logic
2. `features/catalog/router.py` - API endpoints
3. `domain/schemas/catalog.py` - Request/response schemas
4. Update main router to include catalog routes

Shall we begin with the service layer?
