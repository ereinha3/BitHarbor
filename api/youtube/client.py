"""Helpers for fetching metadata and downloading content from YouTube."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yt_dlp

logger = logging.getLogger(__name__)

DEFAULT_OUTTMPL = "%(title)s.%(ext)s"
VIDEO_FORMAT_DEFAULT = "bestvideo+bestaudio/best"
AUDIO_FORMAT_DEFAULT = "bestaudio/best"


@dataclass(slots=True, frozen=True)
class YouTubeSearchResult:
    """Represents a single YouTube search match."""

    video_id: str
    title: str
    url: str
    metadata: Mapping[str, Any]


@dataclass(slots=True, frozen=True)
class YouTubeDownloadResult:
    """Details about a completed download."""

    url: str
    filepaths: List[Path]
    metadata: Mapping[str, Any]


class YouTubeDownloadError(RuntimeError):
    """Raised when a YouTube download fails."""


class YouTubeClient:
    """Thin wrapper around :mod:`yt_dlp` for deterministic video/audio downloads."""

    def __init__(self, base_options: Optional[Mapping[str, Any]] = None) -> None:
        self._base_options = dict(base_options or {})

    # ---------------------------------------------------------------------
    # Metadata & Search
    # ---------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_metadata: bool = True,
    ) -> List[YouTubeSearchResult]:
        """Search YouTube and return up to ``max_results`` entries."""

        search_url = f"ytsearch{max_results}:{query}"
        opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
            **self._base_options,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_url, download=False)

        entries = info.get("entries", [])
        results: List[YouTubeSearchResult] = []
        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id")
            title = entry.get("title") or ""
            url = entry.get("webpage_url") or entry.get("url")
            if not (video_id and url):
                continue
            metadata = entry
            if include_metadata and entry.get("_type") == "url" and entry.get("ie_result") == "youtube":
                metadata = self.fetch_metadata(url)
            results.append(
                YouTubeSearchResult(
                    video_id=video_id,
                    title=title,
                    url=url,
                    metadata=metadata,
                )
            )
        return results

    def fetch_metadata(self, url: str) -> Mapping[str, Any]:
        """Return the metadata for *url* without downloading the media."""

        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            **self._base_options,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    # ---------------------------------------------------------------------
    # Downloads
    # ---------------------------------------------------------------------
    def download_video(
        self,
        url: str,
        *,
        destination: Path,
        filename: Optional[str] = None,
        quality: str = VIDEO_FORMAT_DEFAULT,
        merge_format: str = "mp4",
    ) -> YouTubeDownloadResult:
        """Download *url* as an MP4 (default) video."""

        destination.mkdir(parents=True, exist_ok=True)
        outtmpl = self._build_outtmpl(destination, filename)
        opts: Dict[str, Any] = {
            "format": quality,
            "outtmpl": outtmpl,
            "merge_output_format": merge_format,
            "quiet": True,
            "noplaylist": True,
            **self._base_options,
        }
        return self._run_download(url, opts)

    def download_audio(
        self,
        url: str,
        *,
        destination: Path,
        filename: Optional[str] = None,
        quality: str = AUDIO_FORMAT_DEFAULT,
        audio_format: str = "mp3",
        audio_bitrate: str = "192",
    ) -> YouTubeDownloadResult:
        """Download *url* as an audio file (default: MP3)."""

        destination.mkdir(parents=True, exist_ok=True)
        outtmpl = self._build_outtmpl(destination, filename)
        opts: Dict[str, Any] = {
            "format": quality,
            "outtmpl": outtmpl,
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_bitrate,
                }
            ],
            "prefer_ffmpeg": True,
            **self._base_options,
        }
        return self._run_download(url, opts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_download(self, url: str, options: Mapping[str, Any]) -> YouTubeDownloadResult:
        try:
            with yt_dlp.YoutubeDL(dict(options)) as ydl:
                info = ydl.extract_info(url, download=True)
                filepaths = self._resolve_filepaths(info)
        except Exception as exc:  # noqa: BLE001
            logger.error("YouTube download failed for %s: %s", url, exc)
            raise YouTubeDownloadError(str(exc)) from exc

        return YouTubeDownloadResult(url=url, filepaths=filepaths, metadata=info)

    def _build_outtmpl(self, destination: Path, filename: Optional[str]) -> str:
        base = filename or DEFAULT_OUTTMPL
        if "%(ext)" not in base:
            base = base + ".%(ext)s"
        return str(destination / base)

    def _resolve_filepaths(self, info: Mapping[str, Any]) -> List[Path]:
        paths: List[Path] = []
        requested = info.get("requested_downloads") or []
        for download in requested:
            filepath = download.get("filepath")
            if filepath:
                paths.append(Path(filepath))
        if not paths:
            with yt_dlp.YoutubeDL() as ydl:
                paths.append(Path(ydl.prepare_filename(info)))
        return paths
