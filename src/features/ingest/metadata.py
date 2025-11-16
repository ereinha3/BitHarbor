from __future__ import annotations

import json
from typing import Any, Mapping

from blake3 import blake3


def _flatten_metadata(metadata: Mapping[str, Any], prefix: str | None = None) -> list[str]:
    parts: list[str] = []
    for key in sorted(metadata.keys()):
        value = metadata[key]
        if value is None:
            continue
        label = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            parts.extend(_flatten_metadata(value, label))
        elif isinstance(value, (list, tuple, set)):
            joined = ", ".join(str(item) for item in value if item not in (None, ""))
            if joined:
                parts.append(f"{label}:{joined}")
        else:
            text = str(value).strip()
            if text:
                parts.append(f"{label}:{text}")
    return parts


def build_text_blob(metadata: Mapping[str, Any] | None, fallback: str) -> str:
    if not metadata:
        return fallback.lower()
    parts = _flatten_metadata(metadata)
    if not parts:
        return fallback.lower()
    joined = " | ".join(parts)
    return " ".join(joined.lower().split())


def compute_meta_fingerprint(text_blob: str) -> str:
    return blake3(text_blob.encode("utf-8")).hexdigest()


def serialize_metadata(metadata: Mapping[str, Any] | None) -> str | None:
    if metadata is None:
        return None
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))

