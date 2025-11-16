from __future__ import annotations

try:
from .service import AnnResult, AnnService, get_ann_service
except ModuleNotFoundError:  # pragma: no cover
    AnnResult = None
    AnnService = None

    def get_ann_service(*_args, **_kwargs):
        raise ModuleNotFoundError("ANN service dependencies are missing.")

__all__ = ["AnnResult", "AnnService", "get_ann_service"]

