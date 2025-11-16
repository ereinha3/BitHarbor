from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class IdMap(Base):
    """Maps ANN vector row IDs to media identifiers."""

    __tablename__ = "ann_id_map"

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    vector_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    media_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

