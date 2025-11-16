from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from passlib.context import CryptContext

from db.base import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Admin(Base):
    """Admin user with authentication capabilities."""
    
    __tablename__ = "admins"
    
    # Primary Key
    admin_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", 
        secondary="admin_participant_links",
        back_populates="admins"
    )
    
    def set_password(self, password: str) -> None:
        """Hash and set the password."""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the hashed password."""
        return pwd_context.verify(password, self.hashed_password)
    
    @classmethod
    def get_all_hashes(cls, session) -> list[str]:
        """Get all password hashes (for migration/admin purposes only)."""
        from sqlalchemy import select
        result = session.execute(select(cls.hashed_password))
        return [row[0] for row in result.all()]
    
    @classmethod
    async def hash_exists(cls, session, password_hash: str) -> bool:
        """Check if a password hash already exists (unlikely but for completeness)."""
        from sqlalchemy import select
        result = await session.execute(
            select(cls).where(cls.hashed_password == password_hash)
        )
        return result.scalar_one_or_none() is not None


class Participant(Base):
    """Participant associated with admin accounts."""
    
    __tablename__ = "participants"
    
    # Primary Key
    participant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Profile
    handle: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Role and preferences
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    preferences_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    admins: Mapped[list["Admin"]] = relationship(
        "Admin",
        secondary="admin_participant_links",
        back_populates="participants"
    )


class AdminParticipantLink(Base):
    """Many-to-many association between admins and participants."""
    
    __tablename__ = "admin_participant_links"
    
    admin_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("admins.admin_id", ondelete="CASCADE"),
        primary_key=True
    )
    participant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("participants.participant_id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # When the association was created
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
