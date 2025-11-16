from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.auth import AdminRead, AuthMeResponse, AuthSetupRequest, LoginRequest, TokenResponse
from features.auth.dependencies import (
    get_auth_service,
    get_current_admin,
)
from features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/setup", response_model=TokenResponse)
async def auth_setup(
    payload: AuthSetupRequest,
    session: AsyncSession = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.bootstrap_admin(session, payload)


@router.post("/login", response_model=TokenResponse)
async def auth_login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.authenticate(session, payload)


@router.get("/me", response_model=AuthMeResponse)
async def auth_me(admin=Depends(get_current_admin)) -> AuthMeResponse:
    return AuthMeResponse(admin=AdminRead.model_validate(admin))

