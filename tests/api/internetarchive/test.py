from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

pytestmark = pytest.mark.api_internetarchive

import internetarchive as ia
from src.api.internetarchive import (
    InternetArchiveClient,
    InternetArchiveDownloadError,
    InternetArchiveSearchResult,
)


class DummySession:
    """Simple stand-in for an ArchiveSession."""


@pytest.fixture(autouse=True)
def patch_get_session(monkeypatch: pytest.MonkeyPatch) -> DummySession:
    session = DummySession()
    monkeypatch.setattr(ia, "get_session", lambda *_, **__: session)
    return session


def test_search_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    hits: List[Dict[str, Any]] = [
        {"identifier": "item_one", "title": "First Item", "downloads": 42},
        {"identifier": "item_two", "downloads": 7},
        {"identifier": None, "title": "missing id"},  # ignored
    ]

    def fake_search_items(query: str, params: Dict[str, Any], session: DummySession) -> List[Dict[str, Any]]:
        assert query == "dogs"
        assert params["rows"] == 5
        assert params["page"] == 2
        assert params["fields"] == "title,downloads"
        assert params["sorts"] == "downloads desc"
        assert isinstance(session, DummySession)
        return hits

    monkeypatch.setattr(ia, "search_items", fake_search_items)

    client = InternetArchiveClient()
    results = list(
        client.search(
            "dogs",
            fields=["title", "downloads"],
            sorts=["downloads desc"],
            rows=5,
            page=2,
        )
    )

    assert len(results) == 2
    assert results[0] == InternetArchiveSearchResult(
        identifier="item_one",
        title="First Item",
        metadata=hits[0],
    )
    assert results[1].identifier == "item_two"
    assert results[1].title is None


def test_download_prefers_torrent_then_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: List[bool] = []

    def fake_download(
        identifier: str,
        destdir: str,
        *,
        session: DummySession,
        glob_pattern: str | None,
        prefer_torrent: bool,
        ignore_existing: bool,
        checksum: bool,
        retries: int | None,
    ) -> None:
        calls.append(prefer_torrent)
        assert identifier == "example_item"
        assert Path(destdir) == tmp_path
        assert glob_pattern == "*.mp4"
        assert ignore_existing is True
        assert checksum is False
        assert retries == 3
        if prefer_torrent:
            raise RuntimeError("torrent unavailable")
        (Path(destdir) / "file.mp4").write_bytes(b"data")

    monkeypatch.setattr(ia, "download", fake_download)

    client = InternetArchiveClient()
    dest = client.download(
        "example_item",
        destination=tmp_path,
        glob_pattern="*.mp4",
        prefer_torrent=True,
        retries=3,
    )

    assert dest == tmp_path
    assert calls == [True, False]  # tried torrent, then HTTP fallback
    assert (tmp_path / "file.mp4").exists()


def test_download_raises_when_all_strategies_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def failing_download(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
        raise RuntimeError("failure")

    monkeypatch.setattr(ia, "download", failing_download)

    client = InternetArchiveClient()
    with pytest.raises(InternetArchiveDownloadError):
        client.download("bad_item", destination=tmp_path, prefer_torrent=True)

