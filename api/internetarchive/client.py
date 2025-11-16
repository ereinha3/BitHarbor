"""Utilities for searching and downloading movies from the Internet Archive."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Sequence

from dotenv import load_dotenv
import internetarchive as ia
from internetarchive import ArchiveSession, Item, configure

load_dotenv()

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(os.getenv("HOME", "")) / ".config" / "internetarchive" / "config"
IA_EMAIL = os.getenv("INTERNET_ARCHIVE_EMAIL")
IA_PASSWORD = os.getenv("INTERNET_ARCHIVE_PASSWORD")

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".mpg", ".mpeg", ".webm")
SUBTITLE_EXTENSIONS = (".srt", ".vtt")

if IA_EMAIL and IA_PASSWORD:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    configure(IA_EMAIL, IA_PASSWORD, config_file=str(CONFIG_FILE))


@dataclass(slots=True, frozen=True)
class InternetArchiveSearchResult:
    identifier: str
    title: Optional[str]
    metadata: Mapping[str, Any]


@dataclass
class MovieAssetBundle:
    identifier: str
    title: Optional[str]
    metadata: Mapping[str, Any]
    video_path: Optional[Path]
    cover_art_path: Optional[Path]
    metadata_xml_path: Optional[Path]
    subtitle_paths: list[Path]


class InternetArchiveDownloadError(RuntimeError):
    """Raised when an Internet Archive download fails."""


class InternetArchiveClient:
    """Thin wrapper around the internetarchive library for movie searches/downloads."""

    def __init__(self) -> None:
        if CONFIG_FILE.exists():
            self._session: ArchiveSession = ia.get_session(config_file=str(CONFIG_FILE))
        else:
            self._session = ia.get_session()

    def search_movies(
        self,
        title: str,
        *,
        rows: int = 20,
        enrich: bool = True,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> Iterator[InternetArchiveSearchResult]:
        """Search Internet Archive movie catalog for the given title."""

        query = f'title:"{title}"'
        return self._search(
            query,
            rows=rows,
            enrich=enrich,
            sorts=sorts,
            filters=filters,
            mediatype="movies",
        )

    def collect_movie_assets(
        self,
        identifier: str,
        *,
        destination: Path,
        include_subtitles: bool = True,
        checksum: bool = False,
    ) -> MovieAssetBundle:
        """
        Download the primary assets for a movie (video, cover art, metadata xml, optional subtitles).

        Returns a ``MovieAssetBundle`` describing local paths to each asset.
        """

        metadata = self.fetch_metadata(identifier)
        files = metadata.get("files", [])
        title = metadata.get("metadata", {}).get("title")

        video_file = self._select_video_file(files)
        metadata_xml_file = self._select_metadata_xml(files)
        cover_art_file = self._select_cover_art(files)
        subtitle_files = self._select_subtitles(files) if include_subtitles else []

        download_map: Dict[str, str] = {}
        for remote in [video_file, metadata_xml_file, cover_art_file]:
            if remote:
                download_map[remote] = remote
        for remote in subtitle_files:
            download_map[remote] = remote

        target_dir = destination / identifier
        target_dir.mkdir(parents=True, exist_ok=True)

        if download_map:
            item = self.get_item(identifier)
            item.download(
                destdir=str(destination),
                files=download_map,
                ignore_existing=True,
                checksum=checksum,
            )

        def local_path(name: Optional[str]) -> Optional[Path]:
            return target_dir / name if name else None

        return MovieAssetBundle(
            identifier=identifier,
            title=title,
            metadata=metadata,
            video_path=local_path(video_file),
            cover_art_path=local_path(cover_art_file),
            metadata_xml_path=local_path(metadata_xml_file),
            subtitle_paths=[local_path(name) for name in subtitle_files if local_path(name)],
        )

    def download(
        self,
        identifier: str,
        *,
        destination: Path,
        glob_pattern: str | None = None,
        retries: int | None = 3,
        ignore_existing: bool = True,
        checksum: bool = False,
    ) -> Path:
        """Download an item from archive.org into the provided destination directory."""

        destination.mkdir(parents=True, exist_ok=True)

        def _download() -> bool:
            try:
                ia.download(
                    identifier,
                    destdir=str(destination),
                    glob_pattern=glob_pattern,
                    ignore_existing=ignore_existing,
                    checksum=checksum,
                    retries=retries,
                )
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Internet Archive download failed for %s: %s", identifier, exc)
                return False

        if _download():
            return destination

        raise InternetArchiveDownloadError(
            f"Failed to download Internet Archive item '{identifier}'."
        )

    def _search(
        self,
        query: str,
        *,
        rows: int,
        enrich: bool,
        sorts: Sequence[str] | None,
        filters: Sequence[str] | None,
        mediatype: str | None,
    ) -> Iterator[InternetArchiveSearchResult]:
        params: Dict[str, Any] = {"rows": rows, "page": 1}

        if sorts:
            normalized: list[str] = []
            for sort in sorts:
                token = sort.strip()
                if not token:
                    continue
                if " " not in token:
                    token = f"{token} desc"
                normalized.append(token)
            if normalized:
                params["sort[]"] = normalized

        composed_query = self._compose_query(query, mediatype=mediatype, extra_filters=filters)

        search_results = self._session.search_items(composed_query, params=params)
        for hit in search_results:
            if isinstance(hit, Mapping) and "error" in hit:
                raise RuntimeError(f"Internet Archive API error: {hit['error']}")
            metadata = dict(hit)
            identifier = metadata.get("identifier")
            if not identifier:
                continue
            title = metadata.get("title")
            if enrich:
                item_data = self._safe_fetch_metadata(identifier)
                if item_data:
                    metadata["item_metadata"] = item_data
                    title = title or item_data.get("metadata", {}).get("title")
            yield InternetArchiveSearchResult(identifier=identifier, title=title, metadata=metadata)

    def fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        item = self.get_item(identifier)
        return getattr(item, "item_metadata", {}) or {}

    def get_item(self, identifier: str) -> Item:
        return self._session.get_item(identifier)

    def _safe_fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        try:
            return self.fetch_metadata(identifier)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to enrich metadata for %s: %s", identifier, exc, exc_info=True)
            return {}

    def _compose_query(
        self,
        base_query: str,
        *,
        mediatype: str | None,
        extra_filters: Sequence[str] | None,
    ) -> str:
        segments: list[str] = []
        base_query = base_query.strip()
        if base_query:
            segments.append(f"({base_query})")
        if mediatype:
            segments.append(f"mediatype:({mediatype})")
        if extra_filters:
            segments.extend(extra_filters)
        return " AND ".join(segments) if segments else base_query or "*:*"

    def _select_video_file(self, files: Iterable[Mapping[str, Any]]) -> Optional[str]:
        for file_info in files:
            name = file_info.get("name", "")
            source = file_info.get("source")
            if source == "original" and name.lower().endswith(VIDEO_EXTENSIONS):
                return name
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith(VIDEO_EXTENSIONS):
                return name
        return None

    def _select_metadata_xml(self, files: Iterable[Mapping[str, Any]]) -> Optional[str]:
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_meta.xml"):
                return name
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_files.xml"):
                return name
        return None

    def _select_cover_art(self, files: Iterable[Mapping[str, Any]]) -> Optional[str]:
        for file_info in files:
            if file_info.get("format") == "Item Tile":
                return file_info.get("name")
        for file_info in files:
            if file_info.get("format") == "Thumbnail":
                return file_info.get("name")
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return name
        return None

    def _select_subtitles(self, files: Iterable[Mapping[str, Any]]) -> list[str]:
        subtitles: list[str] = []
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith(SUBTITLE_EXTENSIONS):
                subtitles.append(name)
        return subtitles


def print_nested_dictionary(dictionary, indent=0):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            print("\t" * indent + str(key))
            print_nested_dictionary(value, indent + 1)
        elif isinstance(value, list):
            print("\t" * indent + str(key))
            print_list(value, indent + 1)
        else:
            print("\t" * indent + str(key))
            print("\t" * indent + "\t" + str(value))


def print_list(items, indent=0):
    for item in items:
        if isinstance(item, dict):
            print_nested_dictionary(item, indent)
        else:
            print("\t" * indent + str(item))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query Internet Archive movie metadata.")
    parser.add_argument("query", nargs="+", help="Movie title to search for")
    parser.add_argument("--rows", type=int, default=5, help="Number of results to return")
    parser.add_argument("--sort", dest="sorts", action="append", default=None, help="Sort key (e.g. downloads desc)")
    parser.add_argument(
        "--filter",
        dest="filters",
        action="append",
        default=None,
        help="Additional Lucene filter clauses (e.g. language:eng)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip fetching item metadata for each result",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download each matched item into ~/Downloads",
    )
    args = parser.parse_args()

    client = InternetArchiveClient()
    query_str = " ".join(args.query)

    for result in client.search_movies(
        query_str,
        rows=args.rows,
        enrich=not args.no_enrich,
        sorts=args.sorts,
        filters=args.filters,
    ):
        print(f"{result.identifier} :: {result.title or 'No title'}")
        print_nested_dictionary(result.metadata)
        print()

        if args.download:
            destination = Path.home() / "downloads"
            try:
                client.download(result.identifier, destination=destination)
            except Exception as exc:  # noqa: BLE001
                print(f"Error downloading {result.identifier}: {exc}")
                continue
            else:
                print(f"Downloaded to {destination / result.identifier}")
                print()


