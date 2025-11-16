from __future__ import annotations

from fastapi import APIRouter

from features.auth.router import router as auth_router
from features.ingest.router import router as ingest_router
from features.media.router import router as media_router
from features.participants.router import router as participants_router
from features.search.router import router as search_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(participants_router)
api_router.include_router(ingest_router)
api_router.include_router(search_router)
api_router.include_router(media_router)

