from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

import internetarchive as ia
from internetarchive import ArchiveSession, Item

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class InternetArchiveSearchResult:
    identifier: str
    title: Optional[str]
    metadata: Mapping[str, Any]


class InternetArchiveDownloadError(RuntimeError):
    """Raised when an Internet Archive download fails."""


class InternetArchiveClient:
    """Thin wrapper around the internetarchive library for search and downloads."""

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        config_file: str | None = None,
    ) -> None:
        """
        Parameters:
            access_key: Optional IA access key.
            secret_key: Optional IA secret key.
            config_file: Optional path to an IA configuration file.
        """
        if access_key and secret_key:
            self._session: ArchiveSession = ia.get_session(
                access_key=access_key,
                secret_key=secret_key,
                config_file=config_file,
            )
        elif config_file:
            self._session = ia.get_session(config_file=config_file)
        else:
            self._session = ia.get_session()

    def search(
        self,
        query: str,
        *,
        fields: Sequence[str] | None = None,
        sorts: Sequence[str] | None = None,
        rows: int = 50,
        page: int = 1,
    ) -> Iterator[InternetArchiveSearchResult]:
        """
        Execute a metadata search against archive.org.

        Args:
            query: Lucene-style search query.
            fields: Optional fields to include in results.
            sorts: Optional sort strings, e.g. ["downloads desc"].
            rows: Number of results per page.
            page: Page number (1-based).
        """
        params: dict[str, Any] = {
            "rows": rows,
            "page": page,
        }
        if fields:
            params["fields"] = ",".join(fields)
        if sorts:
            params["sorts"] = ",".join(sorts)

        search = ia.search_items(query, params=params, session=self._session)
        for hit in search:
            metadata = dict(hit)
            identifier = metadata.get("identifier")
            if not identifier:
                continue
            yield InternetArchiveSearchResult(
                identifier=identifier,
                title=metadata.get("title"),
                metadata=metadata,
            )

    def get_item(self, identifier: str) -> Item:
        """Return the raw internetarchive Item for advanced use."""
        return self._session.get_item(identifier)

    def download(
        self,
        identifier: str,
        *,
        destination: Path,
        glob_pattern: str | None = None,
        prefer_torrent: bool = True,
        retries: int | None = 3,
        ignore_existing: bool = True,
        checksum: bool = False,
    ) -> Path:
        """
        Download an item from archive.org.

        Tries torrent delivery first (if enabled) and falls back to HTTP on failure.

        Args:
            identifier: Internet Archive item identifier.
            destination: Directory to place downloaded files.
            glob_pattern: Optional glob filter for item files (e.g. '*.mp4').
            prefer_torrent: Try torrent download first (requires aria2 or builtin support).
            retries: Number of retries for individual files.
            ignore_existing: Skip files that already exist locally.
            checksum: Validate checksums after download.
        Returns:
            Path to the destination directory.
        Raises:
            InternetArchiveDownloadError: if both torrent and HTTP downloads fail.
        """
        destination.mkdir(parents=True, exist_ok=True)

        def _download(use_torrent: bool) -> bool:
            try:
                ia.download(
                    identifier,
                    destdir=str(destination),
                    session=self._session,
                    glob_pattern=glob_pattern,
                    prefer_torrent=use_torrent,
                    ignore_existing=ignore_existing,
                    checksum=checksum,
                    retries=retries,
                )
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Internet Archive download failed (torrent=%s) for %s: %s",
                    use_torrent,
                    identifier,
                    exc,
                )
                return False

        if prefer_torrent and _download(True):
            return destination

        if _download(False):
            return destination

        raise InternetArchiveDownloadError(
            f"Failed to download Internet Archive item '{identifier}'."
        )

