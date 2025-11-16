from __future__ import annotations

from db.models import Movie
from domain.media.movies import MovieMedia


def movie_to_media(movie: Movie) -> MovieMedia:
    return MovieMedia(
        file_hash=movie.file_hash,
        embedding_hash=movie.embedding_hash,
        path=movie.path,
        format=movie.format,
        media_type=movie.media_type,
        catalog_source=movie.catalog_source,
        catalog_id=movie.catalog_id,
        catalog_score=movie.catalog_score,
        catalog_downloads=movie.catalog_downloads,
        poster=movie.poster,
        backdrop=movie.backdrop,
        title=movie.title,
        tagline=movie.tagline,
        overview=movie.overview,
        release_date=movie.release_date,
        year=movie.year,
        runtime_min=movie.runtime_min,
        genres=movie.genres,
        languages=movie.languages,
        vote_average=movie.vote_average,
        vote_count=movie.vote_count,
        cast=movie.cast,
        rating=movie.rating,
    )
