from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ParticipantBase(BaseModel):
    handle: str = Field(..., min_length=3, max_length=64)
    display_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    preferences_json: Optional[str] = None


class ParticipantCreate(ParticipantBase):
    role: Optional[str] = Field(default="viewer")


class ParticipantUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    preferences_json: Optional[str] = None
    role: Optional[str] = None


class ParticipantRead(ParticipantBase):
    participant_id: str

    class Config:
        from_attributes = True


class ParticipantAssignmentRequest(BaseModel):
    role: str = Field(default="viewer")

