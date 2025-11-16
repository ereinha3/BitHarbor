from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import torch
from imagebind import data
from imagebind.models import imagebind_model
from imagebind.models.imagebind_model import ModalityType

from bitharbor.settings import EmbeddingSettings, get_settings
from bitharbor.utils.hashing import canonicalize_vector


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _resolve_device(device_pref: str) -> torch.device:
    if device_pref == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_pref == "cpu":
        return torch.device("cpu")
    # auto
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@dataclass
class EmbeddingResult:
    vector: np.ndarray
    vector_hash: str


class ImageBindService:
    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        app_settings = settings or get_settings().embedding
        self.settings = app_settings
        self.device = _resolve_device(app_settings.device)
        _seed_everything(1337)
        self.model = imagebind_model.imagebind_huge(pretrained=True)
        self.model.eval()
        self.model.to(self.device)

    def _canonicalize(self, tensor: torch.Tensor) -> EmbeddingResult:
        vec = tensor.detach().cpu().numpy().astype(np.float32)
        canonical_vec, vec_hash = canonicalize_vector(vec, round_eps=self.settings.round_eps)
        return EmbeddingResult(vector=canonical_vec, vector_hash=vec_hash)

    def embed_text(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        if not texts:
            return []
        inputs = {
            ModalityType.TEXT: data.load_and_transform_text(list(texts), self.device),
        }
        with torch.no_grad():
            embeddings = self.model(inputs)[ModalityType.TEXT]
        return [self._canonicalize(vec) for vec in embeddings]

    def embed_images(self, image_paths: Sequence[Path]) -> list[EmbeddingResult]:
        paths = [str(Path(path)) for path in image_paths]
        if not paths:
            return []
        inputs = {
            ModalityType.VISION: data.load_and_transform_vision_data(paths, self.device),
        }
        with torch.no_grad():
            embeddings = self.model(inputs)[ModalityType.VISION]
        return [self._canonicalize(vec) for vec in embeddings]

    def embed_audio(self, audio_paths: Sequence[Path]) -> list[EmbeddingResult]:
        paths = [str(Path(path)) for path in audio_paths]
        if not paths:
            return []
        inputs = {
            ModalityType.AUDIO: data.load_and_transform_audio_data(paths, self.device),
        }
        with torch.no_grad():
            embeddings = self.model(inputs)[ModalityType.AUDIO]
        return [self._canonicalize(vec) for vec in embeddings]

    def embed_video(self, video_path: Path) -> EmbeddingResult:
        inputs = {
            ModalityType.VISION: data.load_and_transform_video_data([str(video_path)], self.device),
        }
        with torch.no_grad():
            embeddings = self.model(inputs)[ModalityType.VISION]
        # Expect a single embedding returned for the clip
        return self._canonicalize(embeddings[0])

    def embed_catalog(
        self,
        text_blob: str,
        poster_path: Path | None = None,
        fuse_weight: float | None = None,
    ) -> EmbeddingResult:
        weights = fuse_weight or self.settings.fuse_poster_weight
        text_result = self.embed_text([text_blob])[0]
        if poster_path:
            image_result = self.embed_images([poster_path])[0]
            text_vec = torch.from_numpy(text_result.vector)
            image_vec = torch.from_numpy(image_result.vector)
            combined = 0.8 * text_vec + weights * image_vec
            combined = torch.nn.functional.normalize(combined, dim=0)
            return self._canonicalize(combined)
        return text_result

    def embed_personal_media(self, media_path: Path) -> EmbeddingResult:
        suffix = media_path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            return self.embed_images([media_path])[0]
        return self.embed_video(media_path)

    def embed_query_text(self, query: str) -> np.ndarray:
        result = self.embed_text([query])[0]
        return result.vector


_embedding_service: ImageBindService | None = None


def get_embedding_service() -> ImageBindService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = ImageBindService()
    return _embedding_service

