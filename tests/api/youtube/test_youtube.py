from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

from api.youtube.client import YouTubeClient


class DummyYoutubeDL:
    def __init__(self, opts: Dict[str, Any], entries: List[Dict[str, Any]] | None = None) -> None:
        self.opts = opts
        self.calls: list[Dict[str, Any]] = []
        self.entries = entries or []

    def __enter__(self) -> "DummyYoutubeDL":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        return None

    def extract_info(self, url: str, download: bool) -> Dict[str, Any]:
        self.calls.append({"url": url, "download": download})
        if url.startswith("ytsearch"):
            return {"entries": self.entries}
        info = {
            "id": "abc123",
            "title": "Test Video",
            "requested_downloads": [
                {
                    "filepath": "/tmp/output.mp4",
                }
            ],
            "webpage_url": url,
        }
        return info

    def prepare_filename(self, info: Dict[str, Any]) -> str:
        return "/tmp/fallback.mp4"


@pytest.fixture
def patch_youtube_dl(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    captured: Dict[str, Any] = {}
    entries: List[Dict[str, Any]] = []

    def fake_youtube_dl(opts=None):  # noqa: ANN001
        captured.clear()
        captured.update(opts or {})
        return DummyYoutubeDL(dict(opts or {}), entries=entries)

    import api.youtube.client as module

    monkeypatch.setattr(module.yt_dlp, "YoutubeDL", fake_youtube_dl)
    captured["entries"] = entries
    return captured


def test_search_uses_ytsearch_syntax(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [
        {"id": "abc", "title": "Test", "webpage_url": "https://youtu.be/abc"},
        {"id": "def", "title": "Another", "webpage_url": "https://youtu.be/def"},
    ]

    def fake_youtube_dl(opts=None):  # noqa: ANN001
        return DummyYoutubeDL(dict(opts or {}), entries=entries)

    import api.youtube.client as module

    monkeypatch.setattr(module.yt_dlp, "YoutubeDL", fake_youtube_dl)

    client = YouTubeClient()
    results = client.search("unit testing", max_results=2, include_metadata=False)

    assert len(results) == 2
    assert results[0].video_id == "abc"
    assert results[0].url == "https://youtu.be/abc"


def test_fetch_metadata_uses_skip_download(patch_youtube_dl: Dict[str, Any]) -> None:
    client = YouTubeClient()
    metadata = client.fetch_metadata("https://youtube.com/watch?v=abc")

    assert metadata["id"] == "abc123"
    assert patch_youtube_dl["skip_download"] is True
    assert patch_youtube_dl["noplaylist"] is True


def test_download_video_configures_expected_options(patch_youtube_dl: Dict[str, Any]) -> None:
    client = YouTubeClient()
    result = client.download_video(
        "https://youtube.com/watch?v=abc",
        destination=Path("/tmp"),
        filename="custom",
        quality="best",
        merge_format="mp4",
    )

    assert patch_youtube_dl["format"] == "best"
    assert patch_youtube_dl["merge_output_format"] == "mp4"
    assert patch_youtube_dl["outtmpl"].endswith("custom.%(ext)s")
    assert result.filepaths == [Path("/tmp/output.mp4")]


def test_download_audio_adds_postprocessor(patch_youtube_dl: Dict[str, Any]) -> None:
    client = YouTubeClient()
    client.download_audio(
        "https://youtube.com/watch?v=abc",
        destination=Path("/tmp"),
        filename="audio",
        audio_format="mp3",
        audio_bitrate="192",
    )

    postprocessors = patch_youtube_dl["postprocessors"]
    assert postprocessors[0]["preferredcodec"] == "mp3"
    assert patch_youtube_dl["prefer_ffmpeg"] is True
