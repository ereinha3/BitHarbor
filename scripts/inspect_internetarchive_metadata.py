#!/usr/bin/env python3
"""Inspect Internet Archive metadata and normalized movie mapping."""

from __future__ import annotations

import argparse
from pprint import pprint

from api.catalog.internetarchive import InternetArchiveClient
from api.catalog.internetarchive.metadata_mapper import map_metadata_to_movie
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Internet Archive movie metadata")
    parser.add_argument("identifier", help="Internet Archive identifier, e.g. night_of_the_living_dead")
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip downloading assets; only inspect metadata",
    )
    args = parser.parse_args()

    client = InternetArchiveClient()
    metadata = client.fetch_metadata(args.identifier)

    print("=== Raw metadata keys ===")
    pprint(sorted(metadata.get("metadata", {}).keys()))

    print("\n=== Normalized MovieMedia ===")
    movie = map_metadata_to_movie(args.identifier, metadata)
    pprint(movie.model_dump())

    if not args.no_download:
        bundle = client.download_movie(args.identifier, destination=Path("./downloads"))
        print("\nDownloaded assets to:")
        print(bundle.video_path)


if __name__ == "__main__":
    from pathlib import Path

    main()
