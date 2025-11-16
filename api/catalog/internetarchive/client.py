"""Internet Archive helper tailored for BitHarbor's movie catalog.

The goal of this module is to expose two sharp, predictable primitives:

* ``search_movies`` – build a catalog-style result list for a query
* ``download_movie`` – fetch the primary assets for a single identifier

The implementation intentionally avoids leaking the internetarchive library's
parameters into the rest of the codebase so that future catalog integrations
can share a similar interface.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import internetarchive as ia
from internetarchive import ArchiveSession, Item, configure

from app.settings import get_settings
from domain.media.movies import MovieMedia

from .metadata_mapper import map_metadata_to_movie

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(os.getenv("HOME", "")) / ".config" / "internetarchive" / "config"
_settings = get_settings()
IA_EMAIL = _settings.internet_archive.email
IA_PASSWORD = _settings.internet_archive.password

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".mpg", ".mpeg", ".webm")
SUBTITLE_EXTENSIONS = (".srt", ".vtt")

if IA_EMAIL and IA_PASSWORD:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    configure(IA_EMAIL, IA_PASSWORD, config_file=str(CONFIG_FILE))


@dataclass(slots=True, frozen=True)
class MovieDownloadOptions:
    """Options that influence download behaviour."""

    include_subtitles: bool = True
    checksum: bool = False
    ignore_existing: bool = True


@dataclass(slots=True, frozen=True)
class InternetArchiveSearchResult:
    """Lightweight representation of a catalog hit."""

    identifier: str
    title: str | None = None
    year: int | None = None
    downloads: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    movie: MovieMedia | None = None


@dataclass(slots=True, frozen=True)
class MovieAssetPlan:
    """Description of which remote files we intend to download."""

    identifier: str
    title: str | None
    metadata: Mapping[str, Any]
    video_file: str | None
    metadata_xml_file: str | None
    cover_art_file: str | None
    subtitle_files: tuple[str, ...]
    normalized_metadata: MovieMedia | None


@dataclass(slots=True, frozen=True)
class MovieAssetBundle:
    """Local artefacts produced by ``download_movie``."""

    identifier: str
    title: str | None
    metadata: Mapping[str, Any]
    video_path: Path | None
    cover_art_path: Path | None
    metadata_xml_path: Path | None
    subtitle_paths: tuple[Path, ...]
    normalized_metadata: MovieMedia | None = None


class InternetArchiveDownloadError(RuntimeError):
    """Raised when an Internet Archive download fails."""


class InternetArchiveClient:
    """Thin wrapper around the internetarchive library for movie searches/downloads."""

    def __init__(self, session: ArchiveSession | None = None) -> None:
        if session is not None:
            self._session = session
        elif CONFIG_FILE.exists():
            self._session = ia.get_session(config_file=str(CONFIG_FILE))
        else:
            self._session = ia.get_session()

    def search_movies(
        self,
        title: str,
        limit: int = 20,
        *,
        sorts: Sequence[str] | None = None,
        filters: Sequence[str] | None = None,
    ) -> list[MovieMedia]:
        """Search the Internet Archive movie catalog for ``title``."""

        params: dict[str, Any] = {"rows": max(1, limit), "page": 1}
        sort_tokens = self._normalize_sorts(sorts or ["downloads desc"])
        if sort_tokens:
            params["sort[]"] = sort_tokens

        query = f'title:"{title}"' if title else "*:*"
        composed_query = self._compose_query(
            query,
            mediatype="movies",
            extra_filters=filters,
        )

        best_by_key: dict[tuple[str, int | None], tuple[MovieMedia, int]] = {}
        search_hits = self._session.search_items(composed_query, params=params)
        for hit in search_hits:
            if not isinstance(hit, Mapping):
                continue
            identifier = hit.get("identifier")
            if not identifier:
                continue

            metadata = dict(hit)
            item_metadata = self._safe_fetch_metadata(identifier)
            payload = item_metadata if item_metadata else {"metadata": metadata}
            try:
                movie = map_metadata_to_movie(identifier, payload)
            except Exception:  # noqa: BLE001
                logger.debug("Failed to map IA metadata for %s", identifier, exc_info=True)
                continue

            downloads = self._safe_int(metadata.get("downloads"))
            if downloads is not None:
                movie.catalog_downloads = downloads
                movie.catalog_score = float(downloads)
            if not movie.catalog_id:
                movie.catalog_id = identifier
            movie.catalog_source = movie.catalog_source or "internet_archive"

            key_title = (movie.title or identifier).strip().lower() if movie.title else identifier.lower()
            key = (key_title, movie.year)
            score = downloads or 0
            existing = best_by_key.get(key)
            if existing is None or score > existing[1]:
                best_by_key[key] = (movie, score)

            if len(best_by_key) >= limit:
                # still continue collecting to ensure better score? we already update if better, but once we hit limit we can continue
                continue

        movies = [entry[0] for entry in best_by_key.values()]
        movies.sort(key=lambda m: m.catalog_downloads or 0, reverse=True)
        return movies[:limit]

    def download_movie(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        options: MovieDownloadOptions | None = None,
    ) -> MovieAssetBundle:
        """Download the primary assets for a movie."""

        opts = options or MovieDownloadOptions()
        plan = self.plan_movie_download(identifier, include_subtitles=opts.include_subtitles)

        destination = destination or Path("/home/ethan/tmp")
        download_list: list[str] = []
        for remote in (plan.video_file, plan.metadata_xml_file, plan.cover_art_file):
            if remote:
                download_list.append(remote)
        download_list.extend(plan.subtitle_files)

        destination.mkdir(parents=True, exist_ok=True)
        target_dir = destination / identifier
        target_dir.mkdir(parents=True, exist_ok=True)

        if download_list:
            item = self.get_item(identifier)
            try:
                item.download(
                    destdir=str(target_dir),
                    files=download_list,
                    ignore_existing=opts.ignore_existing,
                    checksum=opts.checksum,
                    no_directory=True,
                )
            except Exception as exc:  # noqa: BLE001
                raise InternetArchiveDownloadError(
                    f"Failed to download Internet Archive item '{identifier}'."
                ) from exc

        def local_path(name: str | None) -> Path | None:
            return target_dir / name if name else None

        subtitle_paths = tuple(
            path
            for path in (local_path(name) for name in plan.subtitle_files)
            if path is not None
        )

        return MovieAssetBundle(
            identifier=identifier,
            title=plan.title,
            metadata=plan.metadata,
            video_path=local_path(plan.video_file),
            cover_art_path=local_path(plan.cover_art_file),
            metadata_xml_path=local_path(plan.metadata_xml_file),
            subtitle_paths=subtitle_paths,
            normalized_metadata=plan.normalized_metadata,
        )

    def collect_movie_assets(
        self,
        identifier: str,
        *,
        destination: Path | None = None,
        include_subtitles: bool = True,
        checksum: bool = False,
    ) -> MovieAssetBundle:
        """Backward-compatible alias for :meth:`download_movie`."""

        options = MovieDownloadOptions(
            include_subtitles=include_subtitles,
            checksum=checksum,
        )
        return self.download_movie(identifier, destination=destination, options=options)

    def plan_movie_download(
        self,
        identifier: str,
        *,
        include_subtitles: bool = True,
    ) -> MovieAssetPlan:
        """Plan which remote files will be downloaded for an item."""

        metadata = self.fetch_metadata(identifier)
        files = metadata.get("files", []) or []
        title = metadata.get("metadata", {}).get("title")

        video_file = self._select_video_file(files)
        metadata_xml_file = self._select_metadata_xml(files)
        cover_art_file = self._select_cover_art(files)
        subtitle_files = tuple(self._select_subtitles(files) if include_subtitles else [])

        normalized = map_metadata_to_movie(identifier, metadata)

        return MovieAssetPlan(
            identifier=identifier,
            title=title,
            metadata=metadata,
            video_file=video_file,
            metadata_xml_file=metadata_xml_file,
            cover_art_file=cover_art_file,
            subtitle_files=subtitle_files,
            normalized_metadata=normalized,
        )

    def fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        item = self.get_item(identifier)
        payload = getattr(item, "item_metadata", {}) or {}
        if not isinstance(payload, Mapping):
            return {}
        return payload

    def get_item(self, identifier: str) -> Item:
        return self._session.get_item(identifier)

    def _safe_fetch_metadata(self, identifier: str) -> Mapping[str, Any]:
        try:
            return self.fetch_metadata(identifier)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to enrich metadata for %s: %s", identifier, exc, exc_info=True)
            return {}

    def _normalize_sorts(self, sorts: Sequence[str] | None) -> list[str]:
        if not sorts:
            return []
        normalized: list[str] = []
        for sort in sorts:
            token = (sort or "").strip()
            if not token:
                continue
            if " " not in token:
                token = f"{token} desc"
            normalized.append(token)
        return normalized

    def _compose_query(
        self,
        base_query: str,
        *,
        mediatype: str | None,
        extra_filters: Sequence[str] | None,
    ) -> str:
        segments: list[str] = []
        query = base_query.strip()
        if query:
            segments.append(f"({query})")
        if mediatype:
            segments.append(f"mediatype:({mediatype})")
        if extra_filters:
            segments.extend(filter(None, (flt.strip() for flt in extra_filters)))
        return " AND ".join(segments) if segments else "*:*"

    def _extract_year(
        self,
        hit_metadata: Mapping[str, Any],
        item_metadata: Mapping[str, Any] | None,
    ) -> int | None:
        sources = (
            hit_metadata.get("year"),
            hit_metadata.get("date"),
        )
        if item_metadata:
            meta = item_metadata.get("metadata", {})
            sources += (
                meta.get("year"),
                meta.get("date"),
            )
        for source in sources:
            year = self._safe_year(source)
            if year is not None:
                return year
        return None

    def _safe_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_year(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            text = str(value)
            year = int(text.split("-")[0])
        except (ValueError, AttributeError):
            return None
        return year if 1800 <= year <= 2100 else None

    def _select_video_file(self, files: Iterable[Mapping[str, Any]]) -> str | None:
        # Prefer original, non-derivative encodes
        for file_info in files:
            name = file_info.get("name", "")
            source = file_info.get("source")
            lowered = name.lower()
            if source == "original" and lowered.endswith(VIDEO_EXTENSIONS) and ".ia." not in lowered:
                return name
        # Fallback to any other non-derivative video
        for file_info in files:
            name = file_info.get("name", "")
            lowered = name.lower()
            if lowered.endswith(VIDEO_EXTENSIONS) and ".ia." not in lowered:
                return name
        # Final fallback: accept a derivative if that's all we have
        for file_info in files:
            name = file_info.get("name", "")
            if name.lower().endswith(VIDEO_EXTENSIONS):
                return name
        return None

    def _select_metadata_xml(self, files: Iterable[Mapping[str, Any]]) -> str | None:
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_meta.xml"):
                return name
        for file_info in files:
            name = file_info.get("name", "")
            if name.endswith("_files.xml"):
                return name
        return None

    def _select_cover_art(self, files: Iterable[Mapping[str, Any]]) -> str | None:
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
