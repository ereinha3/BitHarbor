from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from domain.schemas import (
    ParticipantAssignmentRequest,
    ParticipantCreate,
    ParticipantRead,
    ParticipantUpdate,
)
from features.auth.dependencies import (
    get_auth_service,
    get_current_admin,
)
from features.auth.service import AuthService

router = APIRouter(tags=["participants"])


@router.get("/admin/participants", response_model=list[ParticipantRead])
async def list_admin_participants(
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    service: AuthService = Depends(get_auth_service),
) -> list[ParticipantRead]:
    return await service.participants_for_admin(session, admin.admin_id)


@router.post("/admin/participants", response_model=ParticipantRead, status_code=201)
async def create_participant(
    payload: ParticipantCreate,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    service: AuthService = Depends(get_auth_service),
) -> ParticipantRead:
    return await service.create_participant(session, payload, admin.admin_id)


@router.patch("/admin/participants/{participant_id}", response_model=ParticipantRead)
async def update_participant(
    participant_id: str,
    payload: ParticipantUpdate,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    service: AuthService = Depends(get_auth_service),
) -> ParticipantRead:
    return await service.update_participant(session, participant_id, payload, admin.admin_id)


@router.post("/admin/participants/{participant_id}/assign", response_model=ParticipantRead)
async def assign_participant(
    participant_id: str,
    payload: ParticipantAssignmentRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    service: AuthService = Depends(get_auth_service),
) -> ParticipantRead:
    return await service.assign_participant(session, participant_id, admin.admin_id, payload)


@router.get("/participants/{participant_id}", response_model=ParticipantRead)
async def get_participant(
    participant_id: str,
    session: AsyncSession = Depends(get_session),
    admin=Depends(get_current_admin),
    service: AuthService = Depends(get_auth_service),
) -> ParticipantRead:
    participants = await service.participants_for_admin(session, admin.admin_id)
    for item in participants:
        if item.participant_id == participant_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found.")

