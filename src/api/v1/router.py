from __future__ import annotations

from fastapi import APIRouter

from bitharbor.routers import auth, ingest, media, participants, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(participants.router)
api_router.include_router(ingest.router)
api_router.include_router(search.router)
api_router.include_router(media.router)

