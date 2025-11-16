from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from db.base import Base
from db.session import engine


async def init_db(custom_engine: AsyncEngine | None = None) -> None:
    target_engine = custom_engine or engine
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

