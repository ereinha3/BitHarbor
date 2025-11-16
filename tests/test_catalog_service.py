"""Tests for catalog service integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock imagebind before any imports that depend on it
sys.modules['imagebind'] = MagicMock()
sys.modules['imagebind.data'] = MagicMock()
sys.modules['imagebind.models'] = MagicMock()
sys.modules['imagebind.models.imagebind_model'] = MagicMock()

import pytest

from api.catalog.internetarchive import MovieAssetBundle
from domain.schemas import IngestResponse
from features.catalog.service import CatalogService


@pytest.fixture
def catalog_service(tmp_path, monkeypatch):
    """Create a CatalogService with mocked dependencies."""
    from app.settings import AppSettings, ServerSettings
    from features.catalog.service import CatalogService
    
    # Create settings with tmp_path
    settings = AppSettings(
        server=ServerSettings(
            data_root=tmp_path / "bitharbor",
            host="localhost",
            port=8000,
        )
    )
    settings.server.data_root.mkdir(parents=True, exist_ok=True)
    
    # Create service with mocked dependencies
    service = CatalogService.__new__(CatalogService)
    service.settings = settings
    service.ia_client = MagicMock()
    service.ingest_service = MagicMock()
    
    return service


@pytest.fixture
def mock_ia_bundle():
    """Create a mock MovieAssetBundle."""
    return MovieAssetBundle(
        identifier="fantastic-planet__1973",
        title="Fantastic Planet",
        metadata={
            "metadata": {
                "title": "Fantastic Planet",
                "year": "1973",
                "description": "Animated science fiction film",
                "creator": "René Laloux",
                "runtime": "72:00",
                "language": "eng",
            }
        },
        video_path=Path("/tmp/fantastic-planet__1973/film.mp4"),
        cover_art_path=Path("/tmp/fantastic-planet__1973/poster.jpg"),
        metadata_xml_path=Path("/tmp/fantastic-planet__1973/_meta.xml"),
        subtitle_paths=(Path("/tmp/fantastic-planet__1973/subs.srt"),),
    )


@pytest.mark.anyio
async def test_extract_ia_metadata(mock_ia_bundle, catalog_service):
    """Test metadata extraction from Internet Archive bundle."""
    metadata = catalog_service._extract_ia_metadata(mock_ia_bundle)

    assert metadata["title"] == "Fantastic Planet"
    assert metadata["year"] == 1973
    assert metadata["overview"] == "Animated science fiction film"
    assert metadata["director"] == "René Laloux"
    assert metadata["runtime_min"] == 72
    assert metadata["languages"] == ["eng"]
    assert metadata["ia_identifier"] == "fantastic-planet__1973"


@pytest.mark.anyio
async def test_parse_runtime(catalog_service):
    """Test runtime parsing from various formats."""

    # MM:SS format
    assert catalog_service._parse_runtime("72:00") == 72
    assert catalog_service._parse_runtime("72:30") == 73  # Rounds up

    # HH:MM:SS format
    assert catalog_service._parse_runtime("01:12:00") == 72
    assert catalog_service._parse_runtime("02:30:45") == 151

    # Invalid formats
    assert catalog_service._parse_runtime("") is None
    assert catalog_service._parse_runtime("invalid") is None
    assert catalog_service._parse_runtime(["72:00"]) == 72  # Handle lists


@pytest.mark.anyio
async def test_ingest_from_internet_archive_success(mock_ia_bundle, catalog_service):
    """Test successful download and ingest from Internet Archive."""

    # Mock Path.exists() to return True for the video file
    with patch.object(Path, 'exists', return_value=True):
        # Mock the InternetArchiveClient
        with patch.object(catalog_service.ia_client, "collect_movie_assets") as mock_collect:
            mock_collect.return_value = mock_ia_bundle

            # Mock the IngestService
            mock_ingest_response = IngestResponse(
                media_id="test-media-id",
                file_hash="test-file-hash",
                vector_hash="test-vector-hash",
            )

            with patch.object(catalog_service.ingest_service, "ingest") as mock_ingest:
                # Make the mock return a coroutine for async call
                async def mock_ingest_fn(*args, **kwargs):
                    return mock_ingest_response
                
                mock_ingest.side_effect = mock_ingest_fn

                # Mock session
                mock_session = MagicMock()

                # Call the method
                result = await catalog_service.ingest_from_internet_archive(
                    session=mock_session,
                    identifier="fantastic-planet__1973",
                    download_dir=Path("/tmp"),
                    cleanup_after_ingest=False,  # Don't cleanup for test
                )

                # Verify result
                assert result.media_id == "test-media-id"
                assert result.file_hash == "test-file-hash"
                assert result.vector_hash == "test-vector-hash"

                # Verify InternetArchiveClient was called
                mock_collect.assert_called_once()

                # Verify IngestService was called with correct data
                mock_ingest.assert_called_once()
                ingest_call = mock_ingest.call_args
                ingest_request = ingest_call[0][1]  # Second positional arg

                assert ingest_request.path == str(mock_ia_bundle.video_path)
                assert ingest_request.media_type == "movie"
                assert ingest_request.source_type == "catalog"
                assert ingest_request.metadata["title"] == "Fantastic Planet"
                assert ingest_request.metadata["year"] == 1973
                assert ingest_request.poster_path == str(mock_ia_bundle.cover_art_path)


@pytest.mark.anyio
async def test_ingest_handles_missing_video(catalog_service):
    """Test error handling when video file is missing."""

    # Create bundle with no video path
    bundle = MovieAssetBundle(
        identifier="test",
        title="Test",
        metadata={"metadata": {}},
        video_path=None,
        cover_art_path=None,
        metadata_xml_path=None,
        subtitle_paths=(),
    )

    with patch.object(catalog_service.ia_client, "collect_movie_assets") as mock_collect:
        mock_collect.return_value = bundle

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="No video file downloaded"):
            await catalog_service.ingest_from_internet_archive(
                session=mock_session,
                identifier="test",
            )


def test_extract_ia_metadata_with_minimal_data(catalog_service):
    """Test metadata extraction with minimal Internet Archive data."""

    bundle = MovieAssetBundle(
        identifier="minimal",
        title="Minimal Movie",
        metadata={"metadata": {"title": "Minimal Movie"}},
        video_path=Path("/tmp/video.mp4"),
        cover_art_path=None,
        metadata_xml_path=None,
        subtitle_paths=(),
    )

    metadata = catalog_service._extract_ia_metadata(bundle)

    assert metadata["title"] == "Minimal Movie"
    assert metadata["ia_identifier"] == "minimal"
    # Other fields should be absent
    assert "year" not in metadata
    assert "overview" not in metadata
