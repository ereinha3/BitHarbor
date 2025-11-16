"""Example integration of TMDb client with BitHarbor backend services."""

from __future__ import annotations

from typing import Optional

from api.tmdb import TMDbClient, TMDbMovie, TMDbSearchResult
from app.settings import get_settings


class MovieMetadataService:
    """Service for fetching and enriching movie metadata using TMDb."""

    def __init__(self) -> None:
        settings = get_settings()
        self.tmdb_client = TMDbClient(
            api_key=settings.tmdb.api_key,
            access_token=settings.tmdb.access_token,
        )
        self.default_language = settings.tmdb.language
        self.include_adult = settings.tmdb.include_adult

    async def search_movie(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> list[TMDbSearchResult]:
        """Search for movies by title and optional year.
        
        Args:
            title: Movie title to search
            year: Optional release year to filter results
            
        Returns:
            List of matching movies
        """
        return await self.tmdb_client.search_movie(
            query=title,
            year=year,
            language=self.default_language,
            include_adult=self.include_adult,
        )

    async def get_movie_metadata(
        self,
        movie_id: int,
        include_credits: bool = True,
        include_videos: bool = True,
    ) -> TMDbMovie:
        """Get detailed metadata for a specific movie.
        
        Args:
            movie_id: TMDb movie ID
            include_credits: Include cast and crew information
            include_videos: Include trailers and clips
            
        Returns:
            Detailed movie information
        """
        append = []
        if include_credits:
            append.append("credits")
        if include_videos:
            append.append("videos")

        return await self.tmdb_client.get_movie_details(
            movie_id=movie_id,
            language=self.default_language,
            append_to_response=append if append else None,
        )

    async def find_and_get_details(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> Optional[TMDbMovie]:
        """Search for a movie and return details of the best match.
        
        This is a convenience method that combines search and details fetch.
        
        Args:
            title: Movie title to search
            year: Optional release year
            
        Returns:
            Detailed movie information for the best match, or None if not found
        """
        results = await self.search_movie(title, year)
        if not results:
            return None

        # Get details for the top result (best match)
        return await self.get_movie_metadata(results[0].id)

    def format_for_database(self, movie: TMDbMovie) -> dict:
        """Convert TMDb movie data to BitHarbor database format.
        
        Args:
            movie: TMDb movie object
            
        Returns:
            Dictionary formatted for BitHarbor's movie table
        """
        return {
            "tmdb_id": movie.id,
            "imdb_id": movie.imdb_id,
            "original_title": movie.original_title,
            "title": movie.title,
            "year": int(movie.release_date[:4]) if movie.release_date else None,
            "release_date": movie.release_date,
            "runtime_min": movie.runtime,
            "genres": "|".join(g.name for g in movie.genres) if movie.genres else None,
            "languages": "|".join(
                lang.english_name for lang in movie.spoken_languages
            )
            if movie.spoken_languages
            else None,
            "countries": "|".join(c.name for c in movie.production_countries)
            if movie.production_countries
            else None,
            "overview": movie.overview,
            "tagline": movie.tagline,
            "poster_url": self.tmdb_client.get_image_url(
                movie.poster_path, size="w500"
            ),
            "backdrop_url": self.tmdb_client.get_image_url(
                movie.backdrop_path, size="original"
            ),
            "vote_average": movie.vote_average,
            "vote_count": movie.vote_count,
            "popularity": movie.popularity,
            "budget": movie.budget,
            "revenue": movie.revenue,
            "status": movie.status,
            "homepage": movie.homepage,
            # Store complete metadata as JSON for future use
            "metadata_raw": movie.raw_data,
        }

    def extract_cast_and_crew(self, movie: TMDbMovie) -> dict:
        """Extract cast and crew information from movie details.
        
        Args:
            movie: TMDb movie object with credits appended
            
        Returns:
            Dictionary with cast and crew lists
        """
        cast = []
        crew = []

        if "credits" in movie.raw_data:
            credits = movie.raw_data["credits"]

            # Extract cast (limit to top 20)
            for person in credits.get("cast", [])[:20]:
                cast.append(
                    {
                        "name": person["name"],
                        "character": person["character"],
                        "order": person["order"],
                        "profile_path": person.get("profile_path"),
                    }
                )

            # Extract key crew (director, writer, producer)
            for person in credits.get("crew", []):
                if person["job"] in ["Director", "Writer", "Producer", "Screenplay"]:
                    crew.append(
                        {
                            "name": person["name"],
                            "job": person["job"],
                            "department": person["department"],
                        }
                    )

        return {"cast": cast, "crew": crew}

    async def close(self) -> None:
        """Close the TMDb client."""
        await self.tmdb_client.close()


# Singleton instance
_metadata_service: Optional[MovieMetadataService] = None


def get_metadata_service() -> MovieMetadataService:
    """Get or create the movie metadata service singleton.
    
    Returns:
        MovieMetadataService instance
    """
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MovieMetadataService()
    return _metadata_service


# Example usage in ingest pipeline
async def example_enrich_during_ingest(movie_title: str, year: Optional[int] = None):
    """Example: Enrich movie metadata during ingest.
    
    This shows how to integrate TMDb metadata fetching into your ingest pipeline.
    """
    metadata_service = get_metadata_service()

    # Search and get details
    movie = await metadata_service.find_and_get_details(movie_title, year)

    if not movie:
        print(f"Movie '{movie_title}' not found in TMDb")
        return None

    # Format for database
    db_data = metadata_service.format_for_database(movie)

    # Extract cast and crew
    credits = metadata_service.extract_cast_and_crew(movie)

    print(f"✅ Found: {movie.title} ({movie.release_date})")
    print(f"   TMDb ID: {movie.id}, IMDb ID: {movie.imdb_id}")
    print(f"   Genres: {', '.join(g.name for g in movie.genres)}")
    print(f"   Rating: {movie.vote_average}/10")
    print(f"   Cast: {len(credits['cast'])} actors")
    print(f"   Crew: {len(credits['crew'])} key crew members")

    return {
        "movie": db_data,
        "credits": credits,
    }


# Example usage in search/browse
async def example_enrich_search_results(movie_ids: list[int]):
    """Example: Enrich search results with fresh TMDb data.
    
    This shows how to fetch updated metadata for movies already in your database.
    """
    metadata_service = get_metadata_service()
    enriched = []

    for movie_id in movie_ids:
        try:
            movie = await metadata_service.get_movie_metadata(
                movie_id, include_credits=False, include_videos=True
            )

            enriched.append(
                {
                    "id": movie.id,
                    "title": movie.title,
                    "poster": metadata_service.tmdb_client.get_image_url(
                        movie.poster_path, size="w342"
                    ),
                    "rating": movie.vote_average,
                    "year": movie.release_date[:4] if movie.release_date else None,
                    "has_trailers": len(movie.raw_data.get("videos", {}).get("results", []))
                    > 0,
                }
            )
        except Exception as e:
            print(f"Failed to enrich movie {movie_id}: {e}")
            continue

    return enriched
