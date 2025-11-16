from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.catalog.internetarchive.metadata_mapper import map_metadata_to_movie


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data" / "internetarchive"


def load_fixture(name: str) -> dict:
    fixture_path = FIXTURE_ROOT / name
    with fixture_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_map_metadata_to_movie_extracts_core_fields() -> None:
    payload = load_fixture("fantastic_planet_meta.json")
    movie = map_metadata_to_movie("fantastic-planet-1973-restored-movie-720p-hd", payload)

    assert movie.title.startswith("Fantastic Planet")
    assert movie.year == 1973
    assert movie.languages == ["fre"]
    assert movie.genres and "science fiction" in movie.genres
    assert movie.file_hash is None
    assert movie.path is None
    assert movie.type == "movie"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("01:12:00", 72),
        ("72", 72),
        ("1:12:00", 72),
        ("", None),
        (None, None),
        ("not time", None),
    ],
)
def test_runtime_parsing(raw, expected):
    payload = {"metadata": {"runtime": raw}}
    movie = map_metadata_to_movie("example", payload)
    assert movie.runtime_min == expected
