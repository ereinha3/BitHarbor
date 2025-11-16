"""Service for acquiring and ingesting media from external catalogs."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.catalog.internetarchive import InternetArchiveClient, MovieAssetBundle
from domain.schemas import IngestRequest, IngestResponse
from features.ingest.service import IngestService
from app.settings import AppSettings, get_settings

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for downloading media from external catalogs and ingesting into BitHarbor."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.ia_client = InternetArchiveClient()
        self.ingest_service = IngestService(settings)

    async def ingest_from_internet_archive(
        self,
        session: AsyncSession,
        identifier: str,
        *,
        search_title: Optional[str] = None,
        search_year: Optional[int] = None,
        download_dir: Path | None = None,
        source_type: str = "catalog",
        cleanup_after_ingest: bool = True,
        include_subtitles: bool = True,
    ) -> IngestResponse:
        """Download a movie from Internet Archive and ingest it into BitHarbor.

        This method orchestrates the complete workflow:
        1. Download video, poster, and metadata from archive.org
        2. Extract metadata from Internet Archive
        3. Use search metadata (if provided) for better TMDb matching
        4. Ingest the video file (triggers TMDb enrichment)
        5. Optionally clean up downloaded files

        Args:
            session: Database session for ingestion
            identifier: Internet Archive item identifier (e.g., "fantastic-planet__1973")
            search_title: Movie title from search results (helps TMDb matching)
            search_year: Release year from search results (helps TMDb matching)
            download_dir: Directory for temporary downloads (default: /tmp/bitharbor-downloads)
            source_type: Media source type ("catalog" or "home")
            cleanup_after_ingest: Whether to delete downloaded files after successful ingest
            include_subtitles: Whether to download subtitle files

        Returns:
            IngestResponse with media_id, file_hash, and vector_hash

        Raises:
            InternetArchiveDownloadError: If download fails
            HTTPException: If ingestion fails (file validation, embedding, etc.)
        """
        if download_dir is None:
            download_dir = Path(os.getenv("RAID_TMP_DIR", "/tmp"))

        download_dir = download_dir.expanduser().resolve()
        
        logger.info(f"Starting Internet Archive download and ingest for: {identifier}")

        try:
            # Step 1: Download from Internet Archive
            logger.info(f"Downloading assets from Internet Archive: {identifier}")
            bundle = self.ia_client.collect_movie_assets(
                identifier=identifier,
                destination=download_dir,
                include_subtitles=include_subtitles,
                checksum=False,  # Skip checksum for speed
            )

            if not bundle.video_path or not bundle.video_path.exists():
                raise ValueError(f"No video file downloaded for identifier: {identifier}")

            logger.info(
                f"Downloaded: video={bundle.video_path}, "
                f"poster={bundle.cover_art_path}, "
                f"subtitles={len(bundle.subtitle_paths)}"
            )

            # Step 2: Extract metadata from Internet Archive
            metadata = self._extract_ia_metadata(bundle)
            
            # Step 3: Override with search metadata if provided (better for TMDb matching)
            if search_title:
                logger.info(f"Using search title for TMDb matching: {search_title}")
                metadata["title"] = search_title
            if search_year:
                logger.info(f"Using search year for TMDb matching: {search_year}")
                metadata["year"] = search_year
                
            logger.info(f"Extracted metadata: title='{metadata.get('title')}', year={metadata.get('year')}")

            # Step 4: Build ingest request
            ingest_request = IngestRequest(
                path=str(bundle.video_path),
                media_type="movie",
                source_type=source_type,
                metadata=metadata,
                poster_path=str(bundle.cover_art_path) if bundle.cover_art_path else None,
            )

            # Step 5: Ingest the video (includes TMDb enrichment, embedding, indexing)
            logger.info(f"Ingesting movie into BitHarbor: {bundle.video_path}")
            result = await self.ingest_service.ingest(session, ingest_request)

            logger.info(
                f"Successfully ingested movie from Internet Archive: "
                f"media_id={result.media_id}, identifier={identifier}"
            )

            # Step 6: Cleanup downloaded files if requested
            if cleanup_after_ingest:
                self._cleanup_downloads(bundle, download_dir)

            return result

        except Exception as e:
            logger.error(f"Failed to ingest from Internet Archive: {identifier}, error: {e}")
            # Attempt cleanup on error
            if cleanup_after_ingest:
                try:
                    target_dir = download_dir / identifier
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                        logger.info(f"Cleaned up failed download: {target_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup after error: {cleanup_error}")
            raise

    def _extract_ia_metadata(self, bundle: MovieAssetBundle) -> dict[str, Any]:
        """Extract relevant metadata from Internet Archive bundle.

        Maps Internet Archive metadata fields to BitHarbor/TMDb compatible format.

        Args:
            bundle: MovieAssetBundle from Internet Archive download

        Returns:
            Dictionary with extracted metadata for ingestion
        """
        ia_meta = bundle.metadata.get("metadata", {})

        metadata: dict[str, Any] = {}

        # Title (required)
        metadata["title"] = bundle.title or ia_meta.get("title", "Unknown")

        # Year - try multiple fields
        year_str = ia_meta.get("year") or ia_meta.get("date", "")
        if year_str:
            try:
                # Handle formats like "1973", "1973-01-01", etc.
                year = int(str(year_str).split("-")[0])
                if 1800 <= year <= 2100:  # Sanity check
                    metadata["year"] = year
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse year from: {year_str}")

        # Description/Overview
        description = ia_meta.get("description")
        if description:
            # IA descriptions can be lists or strings
            if isinstance(description, list):
                description = " ".join(str(d) for d in description)
            metadata["overview"] = str(description).strip()

        # Director/Creator
        creator = ia_meta.get("creator") or ia_meta.get("director")
        if creator:
            if isinstance(creator, list):
                creator = ", ".join(str(c) for c in creator)
            metadata["director"] = str(creator).strip()

        # Runtime - parse from duration strings like "01:12:00" or "72:00"
        runtime = ia_meta.get("runtime")
        if runtime:
            try:
                runtime_min = self._parse_runtime(runtime)
                if runtime_min:
                    metadata["runtime_min"] = runtime_min
            except Exception as e:
                logger.warning(f"Could not parse runtime: {runtime}, error: {e}")

        # Language
        language = ia_meta.get("language")
        if language:
            if isinstance(language, list):
                metadata["languages"] = [str(lang) for lang in language]
            else:
                metadata["languages"] = [str(language)]

        # Subject/Keywords (can be used for genre hints)
        subject = ia_meta.get("subject")
        if subject:
            if isinstance(subject, list):
                metadata["keywords"] = [str(s) for s in subject]
            else:
                metadata["keywords"] = [str(subject)]

        # Store original IA identifier for reference
        metadata["ia_identifier"] = bundle.identifier

        logger.debug(f"Extracted IA metadata: {metadata}")
        return metadata

    def _parse_runtime(self, runtime_str: str) -> Optional[int]:
        """Parse runtime string to minutes.

        Handles formats:
        - "72:00" -> 72 minutes
        - "01:12:00" -> 72 minutes
        - "1:12:34" -> 73 minutes (rounded)

        Args:
            runtime_str: Runtime string from Internet Archive

        Returns:
            Runtime in minutes, or None if parsing fails
        """
        if isinstance(runtime_str, list):
            runtime_str = runtime_str[0] if runtime_str else ""

        runtime_str = str(runtime_str).strip()
        if not runtime_str:
            return None

        try:
            parts = runtime_str.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes + (1 if seconds >= 30 else 0)  # Round to nearest minute
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                total_minutes = hours * 60 + minutes + (1 if seconds >= 30 else 0)
                return total_minutes
        except (ValueError, IndexError) as e:
            logger.debug(f"Could not parse runtime '{runtime_str}': {e}")

        return None

    def _cleanup_downloads(self, bundle: MovieAssetBundle, download_dir: Path) -> None:
        """Clean up downloaded files after successful ingestion.

        Args:
            bundle: MovieAssetBundle with file paths
            download_dir: Base download directory
        """
        try:
            # Remove the entire identifier directory
            target_dir = download_dir / bundle.identifier
            if target_dir.exists() and target_dir.is_dir():
                shutil.rmtree(target_dir)
                logger.info(f"Cleaned up downloads: {target_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup downloads for {bundle.identifier}: {e}")


# Singleton instance
_catalog_service: Optional[CatalogService] = None


def get_catalog_service() -> CatalogService:
    """Get or create the catalog service singleton.

    Returns:
        CatalogService instance
    """
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = CatalogService()
    return _catalog_service
