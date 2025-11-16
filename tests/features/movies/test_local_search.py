import asyncio

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models import IdMap, Movie
from features.movies.local_search import MovieLocalSearchService
from infrastructure.embedding.sentence_bert_service import TextEmbeddingResult


class StubEmbeddingService:
    def encode(self, text: str) -> TextEmbeddingResult:  # pragma: no cover - trivial
        vector = np.ones(4, dtype=np.float32)
        return TextEmbeddingResult(vector=vector, vector_hash="stub")


def _setup_db(tmp_path):
    async def runner():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        Session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)

        async with Session() as session:
            movie = Movie(
                embedding_hash="hash1",
                file_hash="filehash1",
                title="Test Movie",
                path=str(tmp_path / "movie.mp4"),
                format="mp4",
            )
            session.add(movie)
            await session.flush()

            session.add(IdMap(row_id=0, vector_hash="hash1", media_id=str(movie.id)))
            await session.commit()

            def stub_vector_search(vector: np.ndarray, k: int):
                return np.array([0]), np.array([0.95], dtype=np.float32)

            service = MovieLocalSearchService(
                settings=object(),
                embedding_service=StubEmbeddingService(),
                vector_search_fn=stub_vector_search,
            )

            response = await service.search(session=session, query="test movie", limit=5)
            assert len(response.results) == 1
            hit = response.results[0]
            assert hit.movie_id == movie.id
            assert hit.media_id == str(movie.id)
            assert hit.score == pytest.approx(0.95)
            assert hit.movie.title == "Test Movie"

            filtered = await service.search(session=session, query="test movie", limit=5, min_score=0.99)
            assert filtered.results == []

        await engine.dispose()

    asyncio.run(runner())


def test_local_search_returns_movie_hit(tmp_path):
    _setup_db(tmp_path)
