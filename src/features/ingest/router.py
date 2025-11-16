from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.schemas import IngestRequest, IngestResponse
from features.auth.dependencies import get_current_admin
from features.ingest.service import IngestService, get_ingest_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/start", response_model=IngestResponse)
async def ingest_start(
    payload: IngestRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    ingest_service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    return await ingest_service.ingest(session, payload)

