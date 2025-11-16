from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np

from app.settings import get_settings
from infrastructure.ann.diskann import DiskAnnIndex
from infrastructure.ann.vector_store import VectorStore
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service

_settings = get_settings()
_sentence_service = get_sentence_bert_service()
_dim = _sentence_service.get_embedding_dimension()
_metric = _settings.ann.metric
_graph_degree = _settings.ann.graph_degree
_complexity = _settings.ann.complexity
_search_memory_budget = _settings.ann.search_memory_budget
_num_threads = _settings.ann.num_threads
_rebuild_batch = max(1, _settings.ann.rebuild_batch)

_base_root = Path(
    Path(os.environ.get("VECTOR_DB_PATH", str(_settings.ann.index_directory.parent)))
)
_movie_root = _base_root / "movies"
_movie_root.mkdir(parents=True, exist_ok=True)

_vectors_path = _movie_root / "vectors.fp32"
_index_directory = _movie_root / "diskann"
_index_directory.mkdir(parents=True, exist_ok=True)

_vector_store = VectorStore(_vectors_path, dim=_dim)
_diskann_index = DiskAnnIndex(
    dim=_dim,
    index_directory=_index_directory,
    metric=_metric,
    graph_degree=_graph_degree,
    complexity=_complexity,
    search_memory_budget=_search_memory_budget,
    num_threads=_num_threads,
)

_pending_rebuild = False


def _ensure_index_built() -> None:
    global _pending_rebuild
    if _vector_store.row_count() == 0:
        _diskann_index.clear()
        _pending_rebuild = False
        return
    if _pending_rebuild or not (_index_directory / "disk.index").exists():
        vectors = _vector_store.read_all()
        if vectors.size > 0:
            _diskann_index.build(vectors)
        _pending_rebuild = False


def append(vector: np.ndarray) -> int:
    global _pending_rebuild
    vec = np.asarray(vector, dtype=np.float32)
    row_id = _vector_store.append(vec)
    if _vector_store.row_count() % _rebuild_batch == 0:
        _ensure_index_built()
    else:
        _pending_rebuild = True
    return row_id


def search(vector: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    _ensure_index_built()
    if _vector_store.row_count() == 0:
        return np.array([]), np.array([])
    query = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(query)
    if norm > 0:
        query = query / norm
    return _diskann_index.search(query, k)

