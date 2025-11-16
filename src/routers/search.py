from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bitharbor.db.session import get_session
from bitharbor.schemas import SearchRequest, SearchResponse
from bitharbor.services.auth.dependencies import get_current_admin
from bitharbor.services.search.service import SearchService, get_search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_media(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    results = await search_service.search(session, payload)
    return SearchResponse(results=results)

