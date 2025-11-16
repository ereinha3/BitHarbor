from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from bitharbor.schemas.participant import ParticipantCreate, ParticipantRead


class AdminBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None


class AdminRead(AdminBase):
    admin_id: str

    class Config:
        from_attributes = True


class AuthSetupRequest(AdminBase):
    password: str = Field(..., min_length=8)
    participants: list[ParticipantCreate] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminRead
    participants: list[ParticipantRead] = Field(default_factory=list)


class AuthMeResponse(BaseModel):
    admin: AdminRead

