from __future__ import annotations

from pathlib import Path

from fastapi import Depends

from api.catalog.internetarchive import InternetArchiveClient, MovieAssetBundle, MovieAssetPlan
from app.settings import AppSettings, get_settings
from domain.catalog import CatalogDownloadResponse

from .search import get_registered_match


class CatalogMatchNotFoundError(RuntimeError):
    """Raised when a download is requested for an unknown match."""


class MovieCatalogDownloadService:
    """Service responsible for planning and executing catalog downloads."""

    def __init__(
        self,
        settings: AppSettings,
        ia_client: InternetArchiveClient | None = None,
    ) -> None:
        self.settings = settings
        self.ia_client = ia_client or InternetArchiveClient()

    def _resolve_match(self, match_key: str):
        match = get_registered_match(match_key)
        if match is None:
            raise CatalogMatchNotFoundError(f"Unknown match key: {match_key}")
        identifier = match.best_candidate.identifier
        if not identifier:
            raise CatalogMatchNotFoundError("Matched candidate is missing an identifier")
        return match, identifier

    def plan(self, match_key: str, destination: Path | None = None) -> CatalogDownloadResponse:
        match, identifier = self._resolve_match(match_key)
        plan: MovieAssetPlan = self.ia_client.plan_movie_download(identifier)
        destination_str = str(destination) if destination else None
        return CatalogDownloadResponse(
            match_key=match_key,
            identifier=identifier,
            title=match.tmdb_movie.title,
            destination=destination_str,
            video_file=plan.video_file,
            metadata_xml_file=plan.metadata_xml_file,
            cover_art_file=plan.cover_art_file,
            subtitle_files=list(plan.subtitle_files),
            downloaded=False,
            video_path=None,
            subtitle_paths=[],
        )

    def download(self, match_key: str, destination: Path | None = None) -> CatalogDownloadResponse:
        match, identifier = self._resolve_match(match_key)
        bundle: MovieAssetBundle = self.ia_client.download_movie(identifier, destination=destination)
        destination_str = str(destination) if destination else None
        return CatalogDownloadResponse(
            match_key=match_key,
            identifier=identifier,
            title=match.tmdb_movie.title,
            destination=destination_str,
            video_file=bundle.video_path.name if bundle.video_path else None,
            metadata_xml_file=bundle.metadata_xml_path.name if bundle.metadata_xml_path else None,
            cover_art_file=bundle.cover_art_path.name if bundle.cover_art_path else None,
            subtitle_files=[path.name for path in bundle.subtitle_paths],
            downloaded=True,
            video_path=str(bundle.video_path) if bundle.video_path else None,
            subtitle_paths=[str(path) for path in bundle.subtitle_paths],
        )


def get_movie_catalog_download_service(
    settings: AppSettings = Depends(get_settings),
) -> MovieCatalogDownloadService:
    return MovieCatalogDownloadService(settings)
