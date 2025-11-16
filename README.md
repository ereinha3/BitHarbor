## BitHarbor Backend

BitHarbor is a local-first media server backend built with FastAPI. It keeps your personal media library searchable with multimodal ImageBind embeddings, a DiskANN-backed ANN index, and SQLite persistence.

### Features
- Deterministic BLAKE3 hashing for files and embeddings
- ImageBind `imagebind_huge` embeddings for text, images, and videos
- Content-addressed storage layout on configurable pool disks
- DiskANN ANN index powered by the official C++/Rust backend
- JWT-protected admin APIs with participant mapping
- Ingest pipeline that hashes, stores, embeds, and indexes media
- REST endpoints for search, metadata, and streaming

### Requirements
- Python 3.11+
- `ffmpeg` (for previews/decoding)
- System dependencies for PyTorch/ImageBind (CUDA optional)

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Copy the example config and customise as needed:
```bash
sudo mkdir -p /etc/bitharbor
sudo cp config.example.yaml /etc/bitharbor/config.yaml
# update secret_key, paths, etc.
```

### Running the API
```bash
BIT_HARBOR_CONFIG=/etc/bitharbor/config.yaml uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Health probe:
```
GET /healthz
```

### First-Time Setup
1. Call `POST /api/v1/auth/setup` with an admin email/password (optionally seed participants).
2. Use the returned token for authenticated endpoints (`Authorization: Bearer ...`).

### Key Endpoints
- `POST /api/v1/auth/login` – obtain JWT token
- `GET /api/v1/admin/participants` – manage participants
- `POST /api/v1/ingest/start` – ingest a media file
- `POST /api/v1/search` – vector search across the library
- `GET /api/v1/media` – list media items
- `GET /api/v1/media/{media_id}` – fetch metadata detail
- `GET /api/v1/media/{media_id}/stream` – stream original media (supports range requests)

All endpoints require a valid admin token.

### systemd Service
An example unit file lives at `scripts/bitharbor.service`. Adjust paths and install:
```bash
sudo cp scripts/bitharbor.service /etc/systemd/system/bitharbor.service
sudo systemctl daemon-reload
sudo systemctl enable --now bitharbor
```

### Development Notes
- Database schema is generated automatically on startup (`SQLite + WAL`).
- DiskANN index assets and vector store persist under `server.data_root`.
- Tests can be added under `tests/` and run via `pytest` (dev extras include test tooling).

### Embedding Model
Embeddings are powered by [ImageBind](https://github.com/facebookresearch/ImageBind) `imagebind_huge`. Ensure GPU drivers are installed if you plan to run on CUDA.
