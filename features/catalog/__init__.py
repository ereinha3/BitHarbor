"""Catalog acquisition feature - download and ingest media from external sources."""

from __future__ import annotations

from .service import CatalogService, get_catalog_service

__all__ = [
    "CatalogService",
    "get_catalog_service",
]
