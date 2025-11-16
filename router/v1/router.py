from __future__ import annotations

from fastapi import APIRouter

from features.auth.router import router as auth_router
from features.ingest.router import router as ingest_router
from features.media.router import router as media_router
from features.participants.router import router as participants_router
from features.search.router import router as search_router

# Type-specific routers
from features.movies.router import router as movies_router
from features.tv.router import router as tv_router
from features.music.router import router as music_router
from features.podcasts.router import router as podcasts_router
from features.videos.router import router as videos_router
from features.personal.router import router as personal_router

api_router = APIRouter(prefix="/api/v1")

# Original general-purpose endpoints (kept for backward compatibility)
api_router.include_router(auth_router)
api_router.include_router(participants_router)
api_router.include_router(ingest_router)
api_router.include_router(search_router)
api_router.include_router(media_router)

# Type-specific endpoints
api_router.include_router(movies_router)
api_router.include_router(tv_router)
api_router.include_router(music_router)
api_router.include_router(podcasts_router)
api_router.include_router(videos_router)
api_router.include_router(personal_router)

