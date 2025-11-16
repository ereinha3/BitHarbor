# BitHarbor TODO

## Status Overview

**Working pieces (as of now):**
- ImageBind embedding service + deterministic hashing (`utils.hashing`, `infrastructure/embedding`)
- DiskANN/HNSW abstraction wired via `AnnService` storing FP32 vectors and rebuilding the graph
- Internet Archive client: movie search, asset selection (video, cover art, metadata XML, subtitles), download helper
- YouTube client: search, metadata fetch, video/audio downloads via `yt-dlp`
- Core SQLAlchemy models mirroring the media schema, async SQLite session helpers

**Missing / Partially implemented:**
- Turnkey admin provisioning (disk enumeration, RAID setup, config writer)
- Full ingest pipeline that moves assets into content-addressable storage, writes SQLite rows, and updates DiskANN
- External catalog reconciliation (TMDB + Internet Archive matching, best-download selection)
- Search API endpoints segmented by media type
- Frontend/auth plumbing to expose the above
- Integration tests / CLI smoke tests

---

## 1. Provisioning & Admin Experience

Goal: a single `bitharbor-admin setup` flow that configures disks, directories, and secrets so users can go from bare metal → running service without manual edits.

### 1.1 Device Discovery
- [ ] Implement `bitharbor-admin devices` CLI command
  - [ ] Use `lsblk --json` to list block devices, size, rotations
  - [ ] Use `blkid` to grab filesystem types/labels
  - [ ] Detect existing mdraid arrays (`mdadm --detail --scan`)
  - [ ] Display mount status (mounted path or free)

### 1.2 Setup Wizard
- [ ] `bitharbor-admin setup` interactive flow
  - [ ] Prompt for optional RAID creation (skip for single disk)
    - [ ] Validate chosen devices are unused and similar size
    - [ ] Support RAID0/1/10 per spec (mdadm create + mkfs)
    - [ ] Optionally dry-run to show planned commands
  - [ ] Prompt for mount point and ensure `/etc/fstab` or systemd `.mount` is written
  - [ ] Ask for:
    - Media root (HDD/RAID path)
    - Index root (SSD, used for `vectors.fp32` + DiskANN index)
    - Config root (e.g. `/etc/bitharbor`)
  - [ ] Generate config YAML/ENV referencing chosen paths
  - [ ] Ensure directories exist with correct ownership (app user/group)
  - [ ] Initialize SQLite database in media root (`Base.metadata.create_all`) and enable WAL mode
  - [ ] Touch empty `vectors.fp32` and index directory in SSD path; set permissions
  - [ ] Create initial admin account (email + password), store hashed password in DB
  - [ ] Output summary and optionally call `systemctl enable --now bitharbor`

### 1.3 Validation & Diagnostics
- [ ] `bitharbor-admin status`
  - [ ] Verify config file exists and is readable
  - [ ] Check SQLite connectivity and schema version
  - [ ] Inspect DiskANN index presence/size
  - [ ] Show ingestion queue status (to be added when pipeline exists)

---

## 2. Ingest Pipeline

Pipeline steps per media item:

1. **Acquire assets** – via Internet Archive bundle, YouTube download, or user upload.
2. **Hashing** – file hash (BLAKE3), metadata fingerprint, vector hash.
3. **Content-addressable copy** – video/audio, cover art, subtitles → `/mnt/pool/<type>/<hash[:2]>/<hash>.<ext>`.
4. **Metadata extraction** – parse JSON/XML, populate `media_core` + type-specific tables, store metadata fingerprint.
5. **Embedding** – produce ImageBind vector (text/image/video) and canonicalize (L2 norm + rounding + hash).
6. **Vector store & ANN** – append to `vectors.fp32` (get new `row_id`), write `idmap` row, trigger DiskANN rebuild when threshold reached.
7. **Preview generation** – optional (ffmpeg to produce thumbnails/3s preview stored on SSD; currently a placeholder).
8. **De-duplication** – if `file_hash` already exists, skip re-embed and just update metadata.

### Tasks
- [ ] `ingest.media_ingest` orchestrator accepting `DownloadedBundle` (`video_path`, `metadata`, etc.)
- [ ] Hashing helpers integrated (re-use `utils.hashing.blake3_file`, `canonicalize_vector`)
- [ ] Content-addressable storage copy with error handling & rollback on failure
- [ ] Metadata parsing for:
  - [ ] Movies (TMDB/IA JSON + fallback) → `movies` table
  - [ ] YouTube/personal uploads → either `online_video` or `personal_media`
  - [ ] Generic fallback if schema incomplete
- [ ] Embedding pipeline for:
  - [ ] Catalog media (text + optional poster weighting per spec)
  - [ ] Personal media (actual image/video frames, EXIF capture date)
- [ ] DiskANN integration hooks: call `AnnService.add_embedding`, handle empty index gracefully, log rebuilds
- [ ] Idempotency: skip ingest if same `file_hash` already associated with `media_core`
- [ ] Unit/integration tests using small sample files

---

## 3. Search & ANN Integration

- [ ] Expose `/search` endpoint that:
  - [ ] Takes `query`, optional `media_type`, `k`
  - [ ] Converts query → ImageBind text embedding
  - [ ] Calls `AnnService.search` with media-type filter (per graph or vector metadata)
  - [ ] Re-ranks using cosine similarity on full FP32 vectors
  - [ ] Hydrates results from SQLite (media_core + type table) and returns JSON (title, preview URL, etc.)
- [ ] Segment ANN indices by media type:
  - Option A: Maintains separate DiskANN instances per media type
  - Option B: Store media type in metadata and filter results post-search
- [ ] `/search` should return empty list when index empty (already handled but test explicitly)
- [ ] Add CLI/debug command to inspect ANN stats (vector count, last rebuild timestamp)

---

## 4. External Catalog & Matching

### 4.1 Catalog Search Flow
- [ ] Query TMDB API + Internet Archive search using user query
- [ ] For each TMDB match:
  - [ ] Identify possible IA downloads (match title/year, adjust for variations)
  - [ ] Rank IA choices by downloads, ratings, runtime match, size
  - [ ] Present single “best” download per movie to user; expose full list of available matches for transparency
- [ ] When user selects a movie:
  - [ ] Download IA bundle via `InternetArchiveClient.collect_movie_assets`
  - [ ] Push output into ingest pipeline (above)
  - [ ] Store derived TMDB metadata (cast, synopsis, poster) in SQLite for richer search results

### 4.2 Personal Upload Metadata
- [ ] For uploaded files (camera rolls, home videos):
  - [ ] Extract EXIF (date, location)
  - [ ] Compute metadata fingerprint (maybe just hash of raw metadata dict, fall back to filename)
  - [ ] store in `personal_media`

---

## 5. API/Frontend & Auth

- [ ] Finish JWT auth integration (ensure `/search`, `/ingest`, `/admin` guard endpoints)
- [ ] Provide CLI or minimal web UI for admin flows:
  - [ ] Setup wizard (under CLI)
  - [ ] Device status
  - [ ] Running ingestion tasks (progress)
- [ ] Provide restful endpoints:
  - [ ] `/search` (text search)
  - [ ] `/media/<id>` (metadata detail, download links)
  - [ ] `/ingest/local` (user uploaded file metadata + path, triggers pipeline)
  - [ ] `/catalog/search` (front-end query hitting TMDB+IA, returning curated choices)
  - [ ] `/catalog/ingest` (user chooses a catalog item to download and ingest)
- [ ] Frontend integration:
  - [ ] React/HTMX or CLI front-end to drive search and ingest flows
  - [ ] Authenticate via login form hitting `/auth/login`, store JWT in local storage/cookies

---

## 6. Testing & Observability

- [ ] Automated tests:
  - [ ] Unit tests for ingest components (hashing, metadata parsing, vector append)
  - [ ] DiskANN integration test (ingest sample vector → search returns item)
  - [ ] Catalog matching test with mocked TMDB + IA data
  - [ ] CLI tests for admin commands (simulate dry-run)
- [ ] Observability/logging:
  - [ ] Structured logs for ingest steps (download, hash, embed, ANN update)
  - [ ] Metrics hooks (vector count, rebuild duration, ingest throughput)
  - [ ] Error alerts for ingestion failures, disk full, ANN rebuild exceptions

---

## 7. Nice-to-haves

- [ ] Optional curated starter pack for first-run installs (download a handful of public domain titles)
- [ ] Web-based admin panel mirroring CLI features (device list, ingest queue)
- [ ] Vector quantization support (FP16/PQ) while keeping FP32 store for re-ranking
- [ ] Background scheduler to refresh TMDB metadata/posters for existing items
- [ ] Offline sync tool to export/import content between machines
