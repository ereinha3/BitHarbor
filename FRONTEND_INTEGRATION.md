# Frontend Integration Guide - Type-Specific Routes

## Quick Reference for bitharbor-web

### Base URL
```
http://localhost:8080/api/v1
```

### Authentication
All endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

Get token via:
```
POST /api/v1/auth/login
{
  "email": "admin@example.com",
  "password": "password"
}
```

---

## Endpoint Patterns

All media types follow the same pattern. Replace `{type}` with one of:
- `movies`
- `tv`
- `music`
- `podcasts`
- `videos`
- `personal`

### 1. Search
```http
POST /api/v1/{type}/search
Content-Type: application/json

{
  "query": "search text",
  "k": 20  // optional, default 20, max 100
}
```

**Response:**
```json
{
  "results": [
    {
      "media_id": "uuid",
      "score": 0.95,
      "type": "movie",
      "title": "Movie Title",
      "preview_url": null
    }
  ]
}
```

### 2. List Media (Pagination)
```http
GET /api/v1/{type}/media?limit=20&offset=0
```

**Response:**
```json
{
  "items": [
    {
      "media_id": "uuid",
      "type": "movie",
      "title": "Title",
      "source_type": "catalog",
      "vector_hash": "hash"
    }
  ],
  "total": 150
}
```

### 3. Get Media Detail
```http
GET /api/v1/{type}/media/{media_id}
```

**Response:**
```json
{
  "media_id": "uuid",
  "type": "movie",
  "title": "Title",
  "source_type": "catalog",
  "vector_hash": "hash",
  "file_hash": "hash",
  "metadata": {
    "title": "Full metadata object",
    "year": 2024,
    "...": "..."
  }
}
```

### 4. Stream Media
```http
GET /api/v1/{type}/media/{media_id}/stream
```

Returns the raw file with proper content-type and supports HTTP range requests for seeking.

### 5. Ingest Media
```http
POST /api/v1/{type}/ingest/start
Content-Type: application/json

{
  "path": "/absolute/path/to/file.mp4",
  "source_type": "catalog",  // or "home"
  "metadata": {
    "title": "Optional Title",
    "year": 2024
  },
  "poster_path": "/path/to/poster.jpg"  // optional
}
```

**Response:**
```json
{
  "media_id": "uuid",
  "file_hash": "blake3_hash",
  "vector_hash": "embedding_hash"
}
```

---

## Example Frontend Usage (TypeScript/React)

```typescript
// API client setup
const API_BASE = 'http://localhost:8080/api/v1';
const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json',
});

// Search movies
async function searchMovies(query: string, k: number = 20) {
  const response = await fetch(`${API_BASE}/movies/search`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query, k }),
  });
  return await response.json();
}

// List TV episodes with pagination
async function listTVEpisodes(page: number = 0, pageSize: number = 20) {
  const offset = page * pageSize;
  const response = await fetch(
    `${API_BASE}/tv/media?limit=${pageSize}&offset=${offset}`,
    { headers: getAuthHeaders() }
  );
  return await response.json();
}

// Get music track details
async function getMusicTrack(mediaId: string) {
  const response = await fetch(
    `${API_BASE}/music/media/${mediaId}`,
    { headers: getAuthHeaders() }
  );
  return await response.json();
}

// Stream video
function getVideoStreamUrl(mediaId: string): string {
  const token = localStorage.getItem('token');
  return `${API_BASE}/videos/media/${mediaId}/stream?token=${token}`;
}

// Ingest personal photo
async function ingestPhoto(filePath: string, metadata?: any) {
  const response = await fetch(`${API_BASE}/personal/ingest/start`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      path: filePath,
      source_type: 'home',
      metadata: metadata || {},
    }),
  });
  return await response.json();
}
```

---

## Media Type Mappings

| Frontend Library | Backend Type | Endpoint Prefix |
|-----------------|--------------|-----------------|
| Movies | `movie` | `/api/v1/movies` |
| TV Shows | `tv` | `/api/v1/tv` |
| Music | `music` | `/api/v1/music` |
| Podcasts | `podcast` | `/api/v1/podcasts` |
| Videos | `video` | `/api/v1/videos` |
| Personal | `personal` | `/api/v1/personal` |

---

## Development Notes

### CORS
The backend has CORS enabled for all origins during development. In production, restrict to your frontend domain.

### File Uploads
The ingest endpoint expects a file path on the backend server. For frontend file uploads, you may need to:
1. Upload file to a temporary location on backend
2. Call ingest with that path
3. Or implement a separate upload endpoint

### Streaming
For video/audio playback in the browser:
```html
<video controls>
  <source src="/api/v1/movies/media/{media_id}/stream" type="video/mp4">
</video>
```

The stream endpoint supports HTTP range requests for seeking.

### Error Handling
All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `404` - Resource not found
- `500` - Server error

Error response format:
```json
{
  "detail": "Error message"
}
```

---

## Testing with curl

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

# Search movies
curl -X POST http://localhost:8080/api/v1/movies/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"action movies","k":10}'

# List TV episodes
curl http://localhost:8080/api/v1/tv/media?limit=10&offset=0 \
  -H "Authorization: Bearer $TOKEN"

# Get music detail
curl http://localhost:8080/api/v1/music/media/{media_id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## OpenAPI Documentation
Once the server is running, view interactive API docs at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
