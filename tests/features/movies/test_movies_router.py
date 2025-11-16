import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models import Movie
from features.movies.router import _fetch_all_movies


def test_fetch_all_movies_returns_movie_metadata(tmp_path):
    async def runner() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        Session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)

        async with Session() as session:
            movie = Movie(
                embedding_hash="hash123",
                title="Test Listing",
                path=str(tmp_path / "test.mp4"),
                format="mp4",
                media_type="movie",
            )
            session.add(movie)
            await session.commit()

            results = await _fetch_all_movies(session)
            assert len(results) == 1
            result = results[0]
            assert result.title == "Test Listing"
            assert result.format == "mp4"

        await engine.dispose()

    asyncio.run(runner())
