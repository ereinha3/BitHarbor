from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

import diskannpy as dap
import numpy as np


class DiskAnnIndex:
    def __init__(
        self,
        dim: int,
        index_directory: Path,
        metric: str = "cosine",
        graph_degree: int = 64,
        complexity: int = 100,
        search_memory_budget: float = 2.0,
        num_threads: int = 0,
    ) -> None:
        self.dim = dim
        self.index_directory = index_directory
        self.metric = metric
        self.graph_degree = graph_degree
        self.complexity = complexity
        self.search_memory_budget = search_memory_budget
        self.num_threads = num_threads or os.cpu_count() or 4
        self._static_index: Optional[dap.StaticDiskIndex] = None

    def _has_index(self) -> bool:
        if not self.index_directory.exists():
            return False
        return any(self.index_directory.iterdir())

    def clear(self) -> None:
        if self.index_directory.exists():
            shutil.rmtree(self.index_directory)
        self.index_directory.mkdir(parents=True, exist_ok=True)
        self._static_index = None

    def build(self, vectors: np.ndarray) -> None:
        if vectors.size == 0:
            self.clear()
            return

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"Expected vectors with shape (N, {self.dim}), got {vectors.shape}"
            )

        if self.index_directory.exists():
            shutil.rmtree(self.index_directory)
        self.index_directory.mkdir(parents=True, exist_ok=True)

        dap.build_disk_index(
            data=vectors,
            metric=self.metric,
            index_directory=str(self.index_directory),
            graph_degree=self.graph_degree,
            complexity=self.complexity,
            search_memory_budget=self.search_memory_budget,
            num_threads=self.num_threads,
            vector_dtype=np.float32,
        )

        self._static_index = dap.StaticDiskIndex(
            index_directory=str(self.index_directory),
            metric=self.metric,
            num_threads=self.num_threads,
        )

    def load(self) -> None:
        if not self._has_index():
            self._static_index = None
            return

        self._static_index = dap.StaticDiskIndex(
            index_directory=str(self.index_directory),
            metric=self.metric,
            num_threads=self.num_threads,
        )

    def search(self, query: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._static_index is None:
            return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

        query = np.asarray(query, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.dim:
            raise ValueError(f"Query must be 1D of length {self.dim}, got {query.shape}")

        response = self._static_index.search(query, k)
        identifiers = response.identifiers.astype(np.int64, copy=False)
        distances = response.distances.astype(np.float32, copy=False)
        return identifiers, distances

