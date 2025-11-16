from __future__ import annotations

from typing import Sequence
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Admin,
    AdminParticipantLink,
    Participant,
)
from domain.schemas.auth import AdminRead, AuthSetupRequest, LoginRequest, TokenResponse
from domain.schemas.participant import (
    ParticipantAssignmentRequest,
    ParticipantCreate,
    ParticipantRead,
    ParticipantUpdate,
)
from app.settings import AppSettings, get_settings
from features.auth.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    async def _admin_exists(self, session: AsyncSession) -> bool:
        stmt = select(func.count(Admin.admin_id))
        count = await session.scalar(stmt)
        return bool(count and count > 0)

    async def bootstrap_admin(
        self, session: AsyncSession, payload: AuthSetupRequest
    ) -> TokenResponse:
        if await self._admin_exists(session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin already configured.",
            )

        admin = Admin(
            admin_id=str(uuid4()),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        session.add(admin)

        participants = await self._create_participants(
            session, payload.participants, admin.admin_id, default_role="owner"
        )

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Failed to create admin.") from exc

        token = create_access_token(admin.admin_id, self.settings.security)
        admin_read = AdminRead.model_validate(admin)
        return TokenResponse(
            access_token=token,
            admin=admin_read,
            participants=participants,
        )

    async def authenticate(self, session: AsyncSession, payload: LoginRequest) -> TokenResponse:
        stmt = select(Admin).where(func.lower(Admin.email) == payload.email.lower())
        admin = await session.scalar(stmt)
        if not admin or not verify_password(payload.password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        participants = await self._participants_for_admin(session, admin.admin_id)
        token = create_access_token(admin.admin_id, self.settings.security)
        admin_read = AdminRead.model_validate(admin)
        return TokenResponse(
            access_token=token,
            admin=admin_read,
            participants=participants,
        )

    async def get_admin(self, session: AsyncSession, admin_id: str) -> Admin:
        stmt = select(Admin).where(Admin.admin_id == admin_id)
        admin = await session.scalar(stmt)
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found.")
        return admin

    async def _create_participants(
        self,
        session: AsyncSession,
        participants: Sequence[ParticipantCreate],
        admin_id: str,
        default_role: str = "viewer",
    ) -> list[ParticipantRead]:
        created: list[ParticipantRead] = []
        for payload in participants:
            participant = Participant(
                participant_id=str(uuid4()),
                handle=payload.handle,
                display_name=payload.display_name,
                email=payload.email,
                preferences_json=payload.preferences_json,
            )
            session.add(participant)
            link = AdminParticipantLink(
                admin_id=admin_id,
                participant_id=participant.participant_id,
                role=payload.role or default_role,
            )
            session.add(link)
            created.append(ParticipantRead.model_validate(participant))
        return created

    async def create_participant(
        self, session: AsyncSession, payload: ParticipantCreate, admin_id: str
    ) -> ParticipantRead:
        participant = Participant(
            participant_id=str(uuid4()),
            handle=payload.handle,
            display_name=payload.display_name,
            email=payload.email,
            preferences_json=payload.preferences_json,
        )
        session.add(participant)
        session.add(
            AdminParticipantLink(
                admin_id=admin_id,
                participant_id=participant.participant_id,
                role=payload.role or "viewer",
            )
        )
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Participant create failed.") from exc
        return ParticipantRead.model_validate(participant)

    async def update_participant(
        self,
        session: AsyncSession,
        participant_id: str,
        payload: ParticipantUpdate,
        admin_id: str,
    ) -> ParticipantRead:
        participant = await self._get_participant_model(session, participant_id)
        if payload.display_name is not None:
            participant.display_name = payload.display_name
        if payload.email is not None:
            participant.email = payload.email
        if payload.preferences_json is not None:
            participant.preferences_json = payload.preferences_json
        if payload.role is not None:
            await self._assign_role(session, participant_id, admin_id, payload.role)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Participant update failed.") from exc
        return ParticipantRead.model_validate(participant)

    async def assign_participant(
        self,
        session: AsyncSession,
        participant_id: str,
        admin_id: str,
        request: ParticipantAssignmentRequest,
    ) -> ParticipantRead:
        participant = await self._get_participant_model(session, participant_id)
        await self._assign_role(session, participant_id, admin_id, request.role)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Participant assignment failed.") from exc
        return ParticipantRead.model_validate(participant)

    async def list_participants(self, session: AsyncSession) -> list[ParticipantRead]:
        stmt = select(Participant)
        result = await session.scalars(stmt)
        return [ParticipantRead.model_validate(item) for item in result.all()]

    async def participants_for_admin(
        self, session: AsyncSession, admin_id: str
    ) -> list[ParticipantRead]:
        return await self._participants_for_admin(session, admin_id)

    async def _participants_for_admin(
        self, session: AsyncSession, admin_id: str
    ) -> list[ParticipantRead]:
        stmt = (
            select(Participant)
            .join(AdminParticipantLink, Participant.participant_id == AdminParticipantLink.participant_id)
            .where(AdminParticipantLink.admin_id == admin_id)
        )
        result = await session.scalars(stmt)
        return [ParticipantRead.model_validate(item) for item in result.all()]

    async def _assign_role(
        self, session: AsyncSession, participant_id: str, admin_id: str, role: str
    ) -> None:
        stmt = (
            select(AdminParticipantLink)
            .where(AdminParticipantLink.admin_id == admin_id)
            .where(AdminParticipantLink.participant_id == participant_id)
        )
        link = await session.scalar(stmt)
        if link:
            link.role = role
        else:
            session.add(
                AdminParticipantLink(
                    admin_id=admin_id,
                    participant_id=participant_id,
                    role=role,
                )
            )

    async def _get_participant_model(self, session: AsyncSession, participant_id: str) -> Participant:
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        participant = await session.scalar(stmt)
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found.")
        return participant

