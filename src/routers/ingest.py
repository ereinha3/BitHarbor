from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bitharbor.db.session import get_session
from bitharbor.schemas import IngestRequest, IngestResponse
from bitharbor.services.auth.dependencies import get_auth_service, get_current_admin
from bitharbor.services.auth.service import AuthService
from bitharbor.services.ingest.service import IngestService, get_ingest_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/start", response_model=IngestResponse)
async def ingest_start(
    payload: IngestRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    ingest_service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    return await ingest_service.ingest(session, payload)

