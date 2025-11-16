# Embedding + DiskANN + SQLite Playbook

This walkthrough shows how to manually ingest a handful of movies, verify the DiskANN index, and run text search without waiting for the full admin UI. Adjust paths as needed for your environment.

> All commands assume you are in the repository root and using the project virtualenv.

---

## 0. Prerequisites

1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Pick data directories** (feel free to change):
   ```bash
   export BITHARBOR_MEDIA_ROOT=/tmp/bitharbor-media
   export BITHARBOR_INDEX_ROOT=/tmp/bitharbor-index
   export BITHARBOR_CONFIG=/tmp/bitharbor-config
   ```

   ```bash
   mkdir -p "$BITHARBOR_MEDIA_ROOT" "$BITHARBOR_INDEX_ROOT" "$BITHARBOR_CONFIG"
   ```

3. **Create a minimal config** (`$BITHARBOR_CONFIG/config.yaml`):
   ```bash
   cat > "$BITHARBOR_CONFIG/config.yaml" <<'YAML'
   server:
     data_root: ${BITHARBOR_MEDIA_ROOT}
     pool_root: ${BITHARBOR_MEDIA_ROOT}/pool
   ann:
     vectors_path: ${BITHARBOR_INDEX_ROOT}/vectors.fp32
     index_directory: ${BITHARBOR_INDEX_ROOT}/diskann
   db:
     url: sqlite+aiosqlite://${BITHARBOR_MEDIA_ROOT}/bitharbor.sqlite
   YAML
   ```

4. **Initialize directories and empty index**
   ```bash
   mkdir -p "$BITHARBOR_MEDIA_ROOT"/pool/video "$BITHARBOR_INDEX_ROOT"/diskann
   : > "$BITHARBOR_INDEX_ROOT"/vectors.fp32
   ```

5. **Create SQLite schema**
   ```bash
   python - <<'PY'
   import asyncio
   from db.init import init_db

   asyncio.run(init_db())
   print("SQLite schema initialized")
   PY
   ```

---

## 1. Download Sample Media

Use the Internet Archive client to pull a public-domain feature into a staging directory:

```bash
python - <<'PY'
from pathlib import Path
from api.catalog.internetarchive import InternetArchiveClient, MovieDownloadOptions

client = InternetArchiveClient()
destination = Path('/tmp/ia-downloads')
destination.mkdir(exist_ok=True, parents=True)

bundle = client.download_movie(
    'fantastic-planet-1973-restored-movie-720p-hd',
    destination=destination,
    options=MovieDownloadOptions(include_subtitles=True),
)
print('Video:', bundle.video_path)
print('Cover:', bundle.cover_art_path)
print('Metadata XML:', bundle.metadata_xml_path)
PY
```

Repeat with another identifier (e.g. `planetesauvage`) so you have a mini dataset.

---

## 2. Manual Ingest Script

The following script performs hashing, content-addressable copy, embedding, SQLite writes, and DiskANN updates for a single bundle. Save it as `scripts/manual_ingest.py` or run inline.

```bash
python - <<'PY'
import asyncio
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from api.catalog.internetarchive import InternetArchiveClient, MovieDownloadOptions
from infrastructure.storage.content_addressable import ContentAddressableStorage
from infrastructure.embedding.imagebind_service import get_embedding_service
from infrastructure.ann.service import get_ann_service
from utils.hashing import blake3_file, canonicalize_vector
from db.session import session_scope
from db.models import MediaCore, Movie, FilePath, IdMap
from utils.hashing import blake3_file

MEDIA_ROOT = Path('${BITHARBOR_MEDIA_ROOT}')
POOL = MEDIA_ROOT / 'pool'
POOL.mkdir(parents=True, exist_ok=True)

CONTENT_STORE = ContentAddressableStorage()
EMBEDDER = get_embedding_service()
ANN = get_ann_service()
client = InternetArchiveClient()

# Assume bundle already downloaded (step 1)
BUNDLE_ROOT = Path('/tmp/ia-downloads')
IDENTIFIER = 'fantastic-planet-1973-restored-movie-720p-hd'

bundle = client.download_movie(
    IDENTIFIER,
    destination=BUNDLE_ROOT,
    options=MovieDownloadOptions(include_subtitles=True),
)
video_path = bundle.video_path
cover_path = bundle.cover_art_path
metadata_xml_path = bundle.metadata_xml_path
metadata = bundle.metadata

if not video_path:
    raise SystemExit('No video file found for bundle!')

file_hash = blake3_file(video_path)
print('File hash:', file_hash)

# 1) Copy to content-addressable storage
stored_video = CONTENT_STORE.store(video_path, modality='video', file_hash=file_hash)

# 2) Compute embedding
vector = EMBEDDER.embed_personal_media(video_path).vector
canonical_vec, vector_hash = canonicalize_vector(vector)
print('Vector hash:', vector_hash)

async def ingest():
    async with session_scope() as session:
        # a) ensure FilePath record
        file_path = FilePath(
            file_hash=file_hash,
            modality='video',
            abs_path=str(stored_video),
            size_bytes=video_path.stat().st_size,
        )
        session.add(file_path)
        await session.flush()

        media_id = str(uuid4())

        core = MediaCore(
            media_id=media_id,
            type='movie',
            file_hash=file_hash,
            vector_hash=vector_hash,
            source_type='catalog',
            embedding_source='content',
            hdd_path_id=file_path.hdd_path_id,
            preview_path=None,
        )
        session.add(core)

        movie = Movie(
            media_id=media_id,
            title=metadata.get('metadata', {}).get('title'),
            original_title=metadata.get('metadata', {}).get('title'),
            release_date=metadata.get('metadata', {}).get('date'),
            overview=metadata.get('metadata', {}).get('description'),
            runtime_min=None,
            genres='|'.join(metadata.get('metadata', {}).get('subject', [])),
            meta_fingerprint=None,
            metadata_raw=str(metadata),
            metadata_enriched=None,
        )
        session.add(movie)
        await session.flush()

        row_id = ANN.add_embedding(
            session, media_id=media_id, vector_hash=vector_hash, vector=canonical_vec
        )
        session.add(IdMap(row_id=row_id, vector_hash=vector_hash, media_id=media_id))

        print(f'Ingested media_id={media_id}, row_id={row_id}')

asyncio.run(ingest())
print('Done.')
PY
```

Re-run the script for each downloaded bundle. After two or three runs you should have a non-empty vector store and index.

---

## 3. Verify SQLite & Content Store

1. **Check SQLite rows**
   ```bash
   sqlite3 "$BITHARBOR_MEDIA_ROOT/bitharbor.sqlite" <<'SQL'
   SELECT media_id, type, file_hash FROM media_core;
   SELECT media_id, title, release_date FROM movies;
   SQL
   ```

2. **Inspect content-addressable storage**
   ```bash
   find "$BITHARBOR_MEDIA_ROOT/pool" -maxdepth 3 -type f
   ```

Expect hashed filenames under `/pool/video/<hh>/<hash>.<ext>`.

---

## 4. Test ANN Search

Use the ANN service + embedder to issue a text query and ensure your ingested items show up.

```bash
python - <<'PY'
from infrastructure.ann.service import get_ann_service
from infrastructure.embedding.imagebind_service import get_embedding_service
from utils.hashing import canonicalize_vector

ann = get_ann_service()
embedder = get_embedding_service()
query_vec = embedder.embed_catalog("psychedelic animated film from 1970s").vector
canon, _ = canonicalize_vector(query_vec)
results = ann.search(canon, k=5)
print(results)
PY
```

Follow up by resolving metadata:

```bash
python - <<'PY'
import asyncio
from infrastructure.ann.service import get_ann_service
from db.session import session_scope

ann = get_ann_service()

async def main():
    async with session_scope() as session:
        results = await ann.resolve_media(session, ann.search(b"", k=5))  # substitute the vector from previous step
        for res in results:
            print(res.media_id, res.score, res.vector_hash)

asyncio.run(main())
PY
```

*(Replace `ann.search(b"",...)` with the actual vector you computed; the snippet shows the pattern.)*

---

## 5. Optional: Text Search via FastAPI

If you want to run the FastAPI app and hit `/search`:

```bash
BIT_HARBOR_CONFIG=$BITHARBOR_CONFIG/config.yaml uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "psychedelic animated film", "k": 5}'
```

Ensure the response includes the media IDs you ingested.

---

## 6. Cleanup (optional)

Remove temporary downloads after verifying:

```bash
rm -rf /tmp/ia-downloads
```

Reset the environment by deleting `$BITHARBOR_MEDIA_ROOT`, `$BITHARBOR_INDEX_ROOT`, and the SQLite DB if needed.

---

## Notes & Tips

- The manual script bypasses any future ingest service; when you formalize the pipeline, migrate the steps into a dedicated module.
- If you get warnings from `yt_dlp` about missing JavaScript runtimes, install `node` or set the extractor args. This only affects YouTube downloads.
- DiskANN rebuilds happen inside `AnnService.add_embedding`; watch logs (`logging.INFO`) to confirm rebuild times.
- For reproducible tests, work inside a throwaway directory under `/tmp` so you can reset quickly.

