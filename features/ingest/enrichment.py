from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from api.tmdb import TMDbClient, TMDbMovie
from app.settings import AppSettings, get_settings
from domain.schemas.enrichment import (
    CastMember,
    CrewMember,
    ImageMetadata,
    MovieMetadata,
)

logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Result of metadata enrichment containing structured data ready for database."""

    def __init__(self, movie: TMDbMovie, client: TMDbClient):
        self.movie = movie
        self._client = client

    def to_movie_metadata(self) -> MovieMetadata:
        """Convert TMDb movie to type-safe MovieMetadata Pydantic model."""
        # Parse release date
        release_date = None
        year = None
        if self.movie.release_date:
            try:
                release_date = datetime.fromisoformat(self.movie.release_date)
                year = release_date.year
            except (ValueError, AttributeError):
                logger.warning(f"Invalid release date format: {self.movie.release_date}")

        # Extract cast
        cast = None
        if "credits" in self.movie.raw_data:
            credits = self.movie.raw_data["credits"]
            cast_data = credits.get("cast", [])[:20]  # Top 20 cast members
            if cast_data:
                cast = [
                    CastMember(
                        name=member.get("name", ""),
                        character=member.get("character", ""),
                        order=member.get("order", 999),
                        profile_path=member.get("profile_path"),
                    )
                    for member in cast_data
                    if member.get("name")
                ]

        # Extract crew
        crew = None
        if "credits" in self.movie.raw_data:
            credits = self.movie.raw_data["credits"]
            crew_data = [
                c for c in credits.get("crew", [])
                if c.get("job") in ["Director", "Writer", "Producer", "Screenplay"]
            ]
            if crew_data:
                crew = [
                    CrewMember(
                        name=member.get("name", ""),
                        job=member.get("job", ""),
                        department=member.get("department", ""),
                    )
                    for member in crew_data
                    if member.get("name") and member.get("job")
                ]

        # Extract images
        posters = None
        backdrops = None
        if "images" in self.movie.raw_data:
            images = self.movie.raw_data["images"]
            poster_data = images.get("posters", [])[:10]  # Top 10 posters
            backdrop_data = images.get("backdrops", [])[:10]  # Top 10 backdrops
            
            if poster_data:
                posters = [
                    ImageMetadata(
                        file_path=img.get("file_path", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                        aspect_ratio=img.get("aspect_ratio"),
                        vote_average=img.get("vote_average"),
                        vote_count=img.get("vote_count"),
                        iso_639_1=img.get("iso_639_1"),
                    )
                    for img in poster_data
                    if img.get("file_path")
                ]
            
            if backdrop_data:
                backdrops = [
                    ImageMetadata(
                        file_path=img.get("file_path", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                        aspect_ratio=img.get("aspect_ratio"),
                        vote_average=img.get("vote_average"),
                        vote_count=img.get("vote_count"),
                        iso_639_1=img.get("iso_639_1"),
                    )
                    for img in backdrop_data
                    if img.get("file_path")
                ]

        # Extract genres, languages, countries
        genres = None
        if self.movie.genres:
            genres = [g.name for g in self.movie.genres]

        languages = None
        if self.movie.spoken_languages:
            languages = [lang.english_name for lang in self.movie.spoken_languages]

        countries = None
        if self.movie.production_countries:
            countries = [c.name for c in self.movie.production_countries]

        # Get full URLs for poster and backdrop
        poster_url = self.get_poster_url() if self.movie.poster_path else None
        backdrop_url = self.get_backdrop_url() if self.movie.backdrop_path else None

        return MovieMetadata(
            tmdb_id=self.movie.id,
            imdb_id=self.movie.imdb_id,
            title=self.movie.title,
            original_title=self.movie.original_title,
            tagline=self.movie.tagline,
            overview=self.movie.overview,
            release_date=release_date,
            year=year,
            status=self.movie.status,
            runtime_min=self.movie.runtime,
            budget=self.movie.budget,
            revenue=self.movie.revenue,
            genres=genres,
            languages=languages,
            countries=countries,
            vote_average=self.movie.vote_average,
            vote_count=self.movie.vote_count,
            popularity=self.movie.popularity,
            cast=cast,
            crew=crew,
            poster_path=self.movie.poster_path,
            backdrop_path=self.movie.backdrop_path,
            posters=posters,
            backdrops=backdrops,
            poster_url=poster_url,
            backdrop_url=backdrop_url,
            homepage=self.movie.homepage,
            adult=self.movie.adult,
        )

    def to_movie_dict(self) -> dict[str, Any]:
        """Convert TMDb movie to database-compatible dictionary for Movie table.
        
        This method provides backward compatibility for database storage.
        The metadata_enriched field stores the type-safe MovieMetadata as JSON.
        """
        # Get type-safe metadata
        metadata = self.to_movie_metadata()
        
        # Convert to database format
        return {
            "tmdb_id": metadata.tmdb_id,
            "imdb_id": metadata.imdb_id,
            "title": metadata.title,
            "original_title": metadata.original_title,
            "year": metadata.year,
            "release_date": metadata.release_date,
            "runtime_min": metadata.runtime_min,
            "genres": "|".join(metadata.genres) if metadata.genres else None,
            "languages": "|".join(metadata.languages) if metadata.languages else None,
            "countries": "|".join(metadata.countries) if metadata.countries else None,
            "overview": metadata.overview,
            "tagline": metadata.tagline,
            "cast_json": json.dumps(
                [member.dict() for member in metadata.cast], ensure_ascii=False
            ) if metadata.cast else None,
            "crew_json": json.dumps(
                [member.dict() for member in metadata.crew], ensure_ascii=False
            ) if metadata.crew else None,
            "posters_json": json.dumps(
                [img.dict() for img in metadata.posters], ensure_ascii=False
            ) if metadata.posters else None,
            "backdrops_json": json.dumps(
                [img.dict() for img in metadata.backdrops], ensure_ascii=False
            ) if metadata.backdrops else None,
            "metadata_raw": json.dumps(self.movie.raw_data, ensure_ascii=False),
            "metadata_enriched": metadata.model_dump_json(),  # Store type-safe metadata as JSON
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
