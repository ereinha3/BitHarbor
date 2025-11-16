from __future__ import annotations

try:  # Optional dependency
    from .imagebind_service import EmbeddingResult, ImageBindService, get_embedding_service
except ModuleNotFoundError:  # pragma: no cover
    EmbeddingResult = None
    ImageBindService = None

    def get_embedding_service(*_args, **_kwargs):
        raise ModuleNotFoundError(
            "ImageBind is not installed. Install the dependency or avoid calling get_embedding_service()."
        )

from .sentence_bert_service import (
    SentenceBertService,
    TextEmbeddingResult,
    get_sentence_bert_service,
)

__all__ = [
    "SentenceBertService",
    "TextEmbeddingResult",
    "get_sentence_bert_service",
]

if EmbeddingResult is not None:
    __all__.extend(["EmbeddingResult", "ImageBindService", "get_embedding_service"])
