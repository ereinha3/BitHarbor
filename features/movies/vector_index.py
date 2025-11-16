from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np

from app.settings import get_settings
from infrastructure.ann.vector_store import VectorStore
from infrastructure.embedding.sentence_bert_service import get_sentence_bert_service

_settings = get_settings()
_sentence_service = get_sentence_bert_service()
_dim = _sentence_service.get_embedding_dimension()
_metric = "l2"
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


# DiskANN integration is currently disabled in this environment.  The vector
# store still persists embeddings, and we perform exact cosine search in
# Python.  Once DiskANN is ready, this module can be swapped to call into the
# high-performance index again.


def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """Return a copy of ``vectors`` with rows L2-normalised."""

    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Avoid divide-by-zero – leave zero vectors untouched.
    safe_norms = np.where(norms == 0.0, 1.0, norms)
    return vectors / safe_norms


def append(vector: np.ndarray) -> int:
    vec = np.asarray(vector, dtype=np.float32)
    row_id = _vector_store.append(vec)
    return row_id


def search(vector: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return the top ``k`` cosine-similar rows for ``vector``."""

    if k <= 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

    stored = _vector_store.read_all()
    if stored.size == 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

    # Normalise stored vectors once for cosine similarity.
    stored = stored.astype(np.float32, copy=False)
    stored_normalised = _normalize_vectors(stored)

    query = np.asarray(vector, dtype=np.float32)
    if query.ndim > 1:
        query = query.ravel()
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)
    query_normalised = query / query_norm

    similarities = stored_normalised @ query_normalised
    order = np.argsort(similarities)[::-1]
    top_k = order[: min(k, similarities.shape[0])]
    return top_k.astype(np.int64), similarities[top_k].astype(np.float32)

