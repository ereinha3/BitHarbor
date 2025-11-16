from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from api.tmdb import TMDbClient, TMDbMovie
from app.settings import AppSettings, get_settings

logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Result of metadata enrichment containing structured data ready for database."""

    def __init__(self, movie: TMDbMovie, client: TMDbClient):
        self.movie = movie
        self._client = client

    def to_movie_dict(self) -> dict[str, Any]:
        """Convert TMDb movie to database-compatible dictionary for Movie table."""
        # Parse release date
        release_date = None
        year = None
        if self.movie.release_date:
            try:
                release_date = datetime.fromisoformat(self.movie.release_date)
                year = release_date.year
            except (ValueError, AttributeError):
                logger.warning(f"Invalid release date format: {self.movie.release_date}")

        # Extract cast and crew
        cast_data = []
        crew_data = []
        if "credits" in self.movie.raw_data:
            credits = self.movie.raw_data["credits"]
            cast_data = credits.get("cast", [])[:20]  # Top 20 cast members
            crew_data = [
                c for c in credits.get("crew", [])
                if c.get("job") in ["Director", "Writer", "Producer", "Screenplay"]
            ]

        # Extract images
        posters = []
        backdrops = []
        if "images" in self.movie.raw_data:
            images = self.movie.raw_data["images"]
            posters = images.get("posters", [])[:10]  # Top 10 posters
            backdrops = images.get("backdrops", [])[:10]  # Top 10 backdrops

        return {
            "tmdb_id": self.movie.id,
            "imdb_id": self.movie.imdb_id,
            "title": self.movie.title,
            "original_title": self.movie.original_title,
            "year": year,
            "release_date": release_date,
            "runtime_min": self.movie.runtime,
            "genres": "|".join(g.name for g in self.movie.genres) if self.movie.genres else None,
            "languages": "|".join(
                lang.english_name for lang in self.movie.spoken_languages
            ) if self.movie.spoken_languages else None,
            "countries": "|".join(
                c.name for c in self.movie.production_countries
            ) if self.movie.production_countries else None,
            "overview": self.movie.overview,
            "tagline": self.movie.tagline,
            "cast_json": json.dumps(cast_data, ensure_ascii=False) if cast_data else None,
            "crew_json": json.dumps(crew_data, ensure_ascii=False) if crew_data else None,
            "posters_json": json.dumps(posters, ensure_ascii=False) if posters else None,
            "backdrops_json": json.dumps(backdrops, ensure_ascii=False) if backdrops else None,
            "metadata_raw": json.dumps(self.movie.raw_data, ensure_ascii=False),
            "metadata_enriched": json.dumps(self.movie.raw_data, ensure_ascii=False),
        }

    def get_poster_url(self, size: str = "w500") -> Optional[str]:
        """Get poster URL for the movie."""
        return self._client.get_image_url(self.movie.poster_path, size=size)

    def get_backdrop_url(self, size: str = "original") -> Optional[str]:
        """Get backdrop URL for the movie."""
        return self._client.get_image_url(self.movie.backdrop_path, size=size)


class MetadataEnrichmentService:
    """Service for enriching media metadata using external APIs (TMDb, etc.)."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._tmdb_client: Optional[TMDbClient] = None

    def _get_tmdb_client(self) -> TMDbClient:
        """Get or create TMDb client instance."""
        if self._tmdb_client is None:
            if not self.settings.tmdb.api_key and not self.settings.tmdb.access_token:
                raise ValueError(
                    "TMDb credentials not configured. Set TMDB_ACCESS_TOKEN "
                    "or TMDB_API_KEY in environment or config file."
                )
            self._tmdb_client = TMDbClient(
                api_key=self.settings.tmdb.api_key,
                access_token=self.settings.tmdb.access_token,
            )
        return self._tmdb_client

    async def enrich_movie(
        self,
        title: str,
        year: Optional[int] = None,
        include_credits: bool = True,
        include_images: bool = True,
    ) -> Optional[EnrichmentResult]:
        """Enrich movie metadata by searching TMDb and fetching details.
        
        Args:
            title: Movie title to search for
            year: Optional release year to improve search accuracy
            include_credits: Include cast and crew information
            include_images: Include posters and backdrops
            
        Returns:
            EnrichmentResult with structured metadata, or None if not found
        """
        client = self._get_tmdb_client()

        try:
            # Search for the movie
            logger.info(f"Searching TMDb for movie: {title}" + (f" ({year})" if year else ""))
            results = await client.search_movie(
                query=title,
                year=year,
                language=self.settings.tmdb.language,
                include_adult=self.settings.tmdb.include_adult,
            )

            if not results:
                logger.warning(f"No TMDb results found for: {title}")
                return None

            # Get details for the best match
            movie_id = results[0].id
            logger.info(f"Found TMDb match: {results[0].title} (ID: {movie_id})")

            # Build append_to_response list
            append = []
            if include_credits:
                append.append("credits")
            if include_images:
                append.append("images")

            movie = await client.get_movie_details(
                movie_id=movie_id,
                language=self.settings.tmdb.language,
                append_to_response=append if append else None,
            )

            logger.info(
                f"Successfully enriched movie: {movie.title} "
                f"(TMDb ID: {movie.id}, IMDb ID: {movie.imdb_id})"
            )

            return EnrichmentResult(movie, client)

        except Exception as e:
            logger.error(f"Error enriching movie metadata for '{title}': {e}")
            return None

    async def enrich_tv_show(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """Enrich TV show metadata (placeholder for future implementation).
        
        Args:
            title: TV show title to search for
            year: Optional first air year
            
        Returns:
            Dictionary with TV show metadata, or None if not found
        """
        # TODO: Implement TV show enrichment when TMDb TV endpoints are added
        logger.warning("TV show enrichment not yet implemented")
        return None

    async def close(self) -> None:
        """Close any open connections."""
        if self._tmdb_client:
            await self._tmdb_client.close()


# Singleton instance
_enrichment_service: Optional[MetadataEnrichmentService] = None


def get_enrichment_service() -> MetadataEnrichmentService:
    """Get or create the metadata enrichment service singleton.
    
    Returns:
        MetadataEnrichmentService instance
    """
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = MetadataEnrichmentService()
    return _enrichment_service
