from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.ann import get_ann_service
from router.v1.router import api_router
from db.init import init_db
from app.settings import get_settings
from app.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.server.log_level)

    app = FastAPI(
        title="BitHarbor",
        version="0.1.0",
        description="Local-first media server backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def on_startup() -> None:
        logger = logging.getLogger(__name__)
        logger.info("BitHarbor backend starting up.")
        await init_db()
        logger.info("Database schema ensured.")
        if settings.ann.enabled:
            try:
        get_ann_service()
            except Exception as exc:  # noqa: BLE001
                logger.warning("ANN service initialisation failed: %s", exc, exc_info=True)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logging.getLogger(__name__).info("BitHarbor backend shutting down.")

    @app.get("/healthz", tags=["system"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)

    return app


app = create_app()

