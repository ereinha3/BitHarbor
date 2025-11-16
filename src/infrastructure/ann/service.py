from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ann.diskann import DiskAnnIndex
from infrastructure.ann.vector_store import VectorStore
from db.models import IdMap
from app.settings import AppSettings, get_settings


@dataclass
class AnnResult:
    row_id: int
    score: float
    vector_hash: str | None = None
    media_id: str | None = None


class AnnService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.vector_store = VectorStore(
            self.settings.ann.vectors_path, dim=self.settings.embedding.dim
        )
        self.index = DiskAnnIndex(
            dim=self.settings.embedding.dim,
            index_directory=self.settings.ann.index_directory,
            metric=self.settings.ann.metric,
            graph_degree=self.settings.ann.graph_degree,
            complexity=self.settings.ann.complexity,
            search_memory_budget=self.settings.ann.search_memory_budget,
            num_threads=self.settings.ann.num_threads,
        )
        self.rebuild_batch = max(1, self.settings.ann.rebuild_batch)
        self._pending_rebuild = False
        self._bootstrap_index()

    def _bootstrap_index(self) -> None:
        row_count = self.vector_store.row_count()
        if row_count == 0:
            self.index.clear()
            return
        vectors = self.vector_store.read_all()
        self.index.build(vectors)

    async def add_embedding(
        self,
        session: AsyncSession,
        media_id: str,
        vector_hash: str,
        vector: np.ndarray,
    ) -> int:
        vec = np.asarray(vector, dtype=np.float32)
        row_id = self.vector_store.append(vec)
        session.add(IdMap(row_id=row_id, vector_hash=vector_hash, media_id=media_id))
        await session.flush()

        if self.vector_store.row_count() % self.rebuild_batch == 0:
            vectors = self.vector_store.read_all()
            self.index.build(vectors)
            self._pending_rebuild = False
        else:
            self._pending_rebuild = True
        return row_id

    def search(self, query_vector: np.ndarray, k: int) -> list[AnnResult]:
        if self._pending_rebuild:
            vectors = self.vector_store.read_all()
            self.index.build(vectors)
            self._pending_rebuild = False

        if self.vector_store.row_count() == 0:
            return []
        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim > 1:
            q = q[0]
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        indices, distances = self.index.search(q, k)
        if indices.size == 0:
            return []

        if self.settings.ann.metric == "cosine":
            scores = 1.0 - distances
        else:
            scores = -distances

        results: list[AnnResult] = []
        for idx, score in zip(indices, scores):
            if idx < 0:
                continue
            results.append(AnnResult(row_id=int(idx), score=float(score)))
        return results[:k]

    async def resolve_media(
        self, session: AsyncSession, results: Sequence[AnnResult]
    ) -> list[AnnResult]:
        if not results:
            return []
        row_ids = [res.row_id for res in results]
        stmt = select(IdMap.row_id, IdMap.vector_hash, IdMap.media_id).where(IdMap.row_id.in_(row_ids))
        rows = await session.execute(stmt)
        mapping = {row_id: (vector_hash, media_id) for row_id, vector_hash, media_id in rows.all()}
        resolved: list[AnnResult] = []
        for res in results:
            vector_hash, media_id = mapping.get(res.row_id, (None, None))
            resolved.append(
                AnnResult(
                    row_id=res.row_id,
                    score=res.score,
                    vector_hash=vector_hash,
                    media_id=media_id,
                )
            )
        return resolved


_ann_service: AnnService | None = None


def get_ann_service() -> AnnService:
    global _ann_service
    if _ann_service is None:
        _ann_service = AnnService()
    return _ann_service

