from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

pytestmark = pytest.mark.api_internetarchive

import internetarchive as ia
from api.internetarchive import (
    InternetArchiveClient,
    InternetArchiveDownloadError,
    InternetArchiveSearchResult,
    MovieAssetBundle,
)


class DummyItem:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.item_metadata = payload
        self.metadata = payload.get("metadata", {})


class DummySession:
    """Simple stand-in for an ArchiveSession."""

    def __init__(self) -> None:
        self.hits: List[Dict[str, Any]] = []
        self.items: Dict[str, Dict[str, Any]] = {}
        self.last_query: str | None = None
        self.last_params: Dict[str, Any] | None = None
        self.download_calls: list[Dict[str, Any]] = []

    def search_items(self, query: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        self.last_query = query
        self.last_params = dict(params or {})
        return list(self.hits)

    def get_item(self, identifier: str) -> DummyItem:
        payload = self.items.get(identifier, {})
        return DummyDownloadableItem(payload, self.download_calls)


class DummyDownloadableItem(DummyItem):
    def __init__(self, payload: Dict[str, Any], download_calls: list[Dict[str, Any]]) -> None:
        super().__init__(payload)
        self._download_calls = download_calls

    def download(self, *, destdir: str, files: Mapping[str, str], ignore_existing: bool, checksum: bool) -> None:  # noqa: D401
        self._download_calls.append(
            {
                "destdir": destdir,
                "files": dict(files),
                "ignore_existing": ignore_existing,
                "checksum": checksum,
            }
        )


@pytest.fixture(autouse=True)
def patch_get_session(monkeypatch: pytest.MonkeyPatch) -> DummySession:
    session = DummySession()
    monkeypatch.setattr(ia, "get_session", lambda *_, **__: session)
    return session


def test_search_movies_returns_results(patch_get_session: DummySession) -> None:
    hits: List[Dict[str, Any]] = [
        {"identifier": "item_one", "title": "First Item", "downloads": 42},
        {"identifier": "item_two", "downloads": 7},
        {"identifier": None, "title": "missing id"},
    ]

    patch_get_session.hits = hits
    patch_get_session.items = {
        "item_one": {"metadata": {"title": "First Item", "collection": "movies"}},
        "item_two": {"metadata": {"title": "Second Title", "collection": "music"}},
    }

    client = InternetArchiveClient()
    results = list(
        client.search_movies(
            "dogs",
            rows=5,
            enrich=True,
            sorts=["downloads desc"],
            filters=["language:eng"],
        )
    )

    assert len(results) == 2
    assert results[0] == InternetArchiveSearchResult(
        identifier="item_one",
        title="First Item",
        metadata={
            **hits[0],
            "item_metadata": patch_get_session.items["item_one"],
        },
    )
    assert results[1].identifier == "item_two"
    assert results[1].title == "Second Title"
    expected_query = "(title:\"dogs\") AND mediatype:(movies) AND language:eng"
    assert patch_get_session.last_query == expected_query
    assert patch_get_session.last_params == {
        "rows": 5,
        "page": 1,
        "sort[]": ["downloads desc"],
    }


def test_search_movies_builds_expected_query(patch_get_session: DummySession) -> None:
    patch_get_session.hits = [{"identifier": "fantasticplanet1973", "title": "Fantastic Planet"}]
    patch_get_session.items = {
        "fantasticplanet1973": {"metadata": {"title": "Fantastic Planet", "year": "1973"}}
    }

    client = InternetArchiveClient()
    results = list(client.search_movies("Fantastic Planet", rows=1, sorts=["downloads desc"]))

    assert results[0].identifier == "fantasticplanet1973"
    assert patch_get_session.last_query == "(title:\"Fantastic Planet\") AND mediatype:(movies)"
    assert patch_get_session.last_params["rows"] == 1


def test_download_prefers_http(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: List[bool] = []

    def fake_download(
        identifier: str,
        destdir: str,
        *,
        glob_pattern: str | None,
        ignore_existing: bool,
        checksum: bool,
        retries: int | None,
    ) -> None:
        calls.append(True)
        assert identifier == "example_item"
        assert Path(destdir) == tmp_path
        assert glob_pattern == "*.mp4"
        assert ignore_existing is True
        assert checksum is False
        assert retries == 3
        (Path(destdir) / "file.mp4").write_bytes(b"data")

    monkeypatch.setattr(ia, "download", fake_download)

    client = InternetArchiveClient()
    dest = client.download(
        "example_item",
        destination=tmp_path,
        glob_pattern="*.mp4",
        retries=3,
    )

    assert dest == tmp_path
    assert calls == [True]
    assert (tmp_path / "file.mp4").exists()


def test_download_raises_when_all_strategies_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def failing_download(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
        raise RuntimeError("failure")

    monkeypatch.setattr(ia, "download", failing_download)

    client = InternetArchiveClient()
    with pytest.raises(InternetArchiveDownloadError):
        client.download("bad_item", destination=tmp_path)


def test_fetch_metadata_returns_payload(patch_get_session: DummySession) -> None:
    identifier = "sample"
    expected = {"metadata": {"title": "Sample Title"}}
    patch_get_session.items = {identifier: expected}

    client = InternetArchiveClient()
    payload = client.fetch_metadata(identifier)

    assert payload == expected


def test_collect_movie_assets_selects_expected_files(tmp_path: Path, patch_get_session: DummySession) -> None:
    identifier = "sample"
    metadata_payload = {
        "metadata": {"title": "Sample"},
        "files": [
            {"name": "SampleFilm.mp4", "source": "original"},
            {"name": "SampleFilm.ia.mp4", "source": "derivative"},
            {"name": "SampleFilm_meta.xml", "source": "metadata"},
            {"name": "__ia_thumb.jpg", "format": "Item Tile"},
            {"name": "SampleFilm.srt"},
        ],
    }
    patch_get_session.items = {identifier: metadata_payload}

    client = InternetArchiveClient()
    bundle: MovieAssetBundle = client.collect_movie_assets(identifier, destination=tmp_path)

    target_dir = tmp_path / identifier
    assert patch_get_session.download_calls == [
        {
            "destdir": str(tmp_path),
            "files": {
                "SampleFilm.mp4": "SampleFilm.mp4",
                "SampleFilm_meta.xml": "SampleFilm_meta.xml",
                "__ia_thumb.jpg": "__ia_thumb.jpg",
                "SampleFilm.srt": "SampleFilm.srt",
            },
            "ignore_existing": True,
            "checksum": False,
        }
    ]
    assert bundle.video_path == target_dir / "SampleFilm.mp4"
    assert bundle.cover_art_path == target_dir / "__ia_thumb.jpg"
    assert bundle.metadata_xml_path == target_dir / "SampleFilm_meta.xml"
    assert bundle.subtitle_paths == [target_dir / "SampleFilm.srt"]
    assert bundle.metadata == metadata_payload

