from __future__ import annotations

import shutil
from pathlib import Path

from app.settings import AppSettings, get_settings


class ContentAddressableStorage:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.pool_root = self.settings.server.pool_root

    def _build_path(self, modality: str, file_hash: str, suffix: str) -> Path:
        shard = file_hash[:2]
        modality_dir = self.pool_root / modality
        return modality_dir / shard / f"{file_hash}{suffix}"

    def store(self, source: Path, modality: str, file_hash: str) -> Path:
        suffix = source.suffix.lower()
        dest = self._build_path(modality, file_hash, suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(source, dest)
        return dest

    def resolve(self, modality: str, file_hash: str, suffix: str) -> Path:
        return self._build_path(modality, file_hash, suffix)

