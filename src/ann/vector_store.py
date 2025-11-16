from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import numpy as np


class VectorStore:
    def __init__(self, path: Path, dim: int) -> None:
        self.path = path
        self.dim = dim
        self.dtype = np.float32
        self.record_bytes = dim * np.dtype(self.dtype).itemsize
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def row_count(self) -> int:
        size = self.path.stat().st_size
        if size == 0:
            return 0
        return size // self.record_bytes

    def append(self, vector: np.ndarray) -> int:
        vec = np.asarray(vector, dtype=self.dtype)
        if vec.shape[-1] != self.dim:
            raise ValueError(f"Vector dim mismatch: expected {self.dim}, got {vec.shape[-1]}")
        with self.path.open("ab") as handle:
            handle.write(np.ascontiguousarray(vec).astype(self.dtype).tobytes())
        return self.row_count() - 1

    def read_rows(self, row_ids: Sequence[int]) -> np.ndarray:
        if not row_ids:
            return np.empty((0, self.dim), dtype=self.dtype)
        count = self.row_count()
        if count == 0:
            return np.empty((0, self.dim), dtype=self.dtype)
        mm = np.memmap(self.path, dtype=self.dtype, mode="r", shape=(count, self.dim))
        return np.array(mm[row_ids])

    def read_all(self) -> np.ndarray:
        count = self.row_count()
        if count == 0:
            return np.empty((0, self.dim), dtype=self.dtype)
        mm = np.memmap(self.path, dtype=self.dtype, mode="r", shape=(count, self.dim))
        return np.array(mm)

