from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from blake3 import blake3


def blake3_file(path: Path, chunk_size: int = 1 << 20) -> str:
    hasher = blake3()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonicalize_vector(
    vector: np.ndarray,
    round_eps: float = 1e-6,
) -> tuple[np.ndarray, str]:
    vec = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    if round_eps > 0:
        decimals = max(0, int(round(-math.log10(round_eps))))
        vec = np.round(vec, decimals=decimals, out=vec)

    byte_view = np.asarray(vec, dtype="<f4", order="C").tobytes()
    vector_hash = blake3(byte_view).hexdigest()
    return vec, vector_hash


def canonicalize_batch(
    vectors: Iterable[np.ndarray], round_eps: float = 1e-6
) -> list[tuple[np.ndarray, str]]:
    return [canonicalize_vector(vec, round_eps=round_eps) for vec in vectors]

