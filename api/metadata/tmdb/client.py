from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
from dotenv import load_dotenv
import os

load_dotenv()


TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")
import httpx

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from domain.media.movies import MovieMedia


@dataclass(slots=True, frozen=True)
class TMDbSearchResult:
    """Represents a movie search result from TMDb."""

    id: int
    title: str
    original_title: str
    release_date: Optional[str]
    overview: Optional[str]
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    popularity: float
    vote_average: float
    vote_count: int
    adult: bool
    original_language: str
    genre_ids: list[int]


@dataclass(slots=True, frozen=True)
class TMDbTvSearchResult:
    """Represents a TV show search result from TMDb."""

    id: int
    name: str
    original_name: str
    first_air_date: Optional[str]
    overview: Optional[str]
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    popularity: float
    vote_average: float
    vote_count: int
    origin_country: list[str]
    original_language: str
    genre_ids: list[int]


@dataclass(slots=True, frozen=True)
class TMDbGenre:
    """Represents a movie genre."""

    id: int
    name: str


@dataclass(slots=True, frozen=True)
class TMDbProductionCompany:
    """Represents a production company."""

    id: int
    name: str
    logo_path: Optional[str]
    origin_country: str


@dataclass(slots=True, frozen=True)
class TMDbProductionCountry:
    """Represents a production country."""

    iso_3166_1: str
    name: str


@dataclass(slots=True, frozen=True)
class TMDbSpokenLanguage:
    """Represents a spoken language."""

    iso_639_1: str
    name: str
    english_name: str


@dataclass(slots=True, frozen=True)
class TMDbMovie:
    """Represents detailed movie information from TMDb."""

    id: int
    title: str
    original_title: str
    tagline: Optional[str]
    overview: Optional[str]
    release_date: Optional[str]
    runtime: Optional[int]  # in minutes
    status: str
    budget: int
    revenue: int
    homepage: Optional[str]
    imdb_id: Optional[str]
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    popularity: float
    vote_average: float
    vote_count: int
    adult: bool
    original_language: str
    genres: list[TMDbGenre]
    production_companies: list[TMDbProductionCompany]
    production_countries: list[TMDbProductionCountry]
    spoken_languages: list[TMDbSpokenLanguage]
    raw_data: dict[str, Any]  # Store the complete raw response


@dataclass(slots=True, frozen=True)
class TMDbTvShow:
    """Represents detailed TV show information from TMDb."""

    id: int
    name: str
    original_name: str
    tagline: Optional[str]
    overview: Optional[str]
    first_air_date: Optional[str]
    last_air_date: Optional[str]
    status: str
    type: str  # Scripted, Reality, etc.
    number_of_seasons: int
    number_of_episodes: int
    homepage: Optional[str]
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    popularity: float
    vote_average: float
    vote_count: int
    original_language: str
    origin_country: list[str]
    genres: list[TMDbGenre]
    production_companies: list[TMDbProductionCompany]
    production_countries: list[TMDbProductionCountry]
    spoken_languages: list[TMDbSpokenLanguage]
    networks: list[dict[str, Any]]  # Network information
    created_by: list[dict[str, Any]]  # Creator information
    raw_data: dict[str, Any]  # Store the complete raw response


class TMDbAPIError(Exception):
    """Raised when TMDb API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"TMDb API error {status_code}: {message}")


class TMDbClient:
    """Client for The Movie Database (TMDb) API v3.
    
    Documentation: https://developer.themoviedb.org/docs
    API Reference: https://developer.themoviedb.org/reference
    """

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    def __init__(self) -> None:
        """Initialize TMDb client.
        
        Args:
            api_key: TMDb API key (v3 auth)
            access_token: TMDb API Read Access Token (Bearer token, preferred)
        """
        self.api_key = TMDB_API_KEY
        self.access_token = TMDB_ACCESS_TOKEN
        self._client = httpx.AsyncClient(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        if self.access_token:
            # Prefer Bearer token authentication
            return {
                "Authorization": f"Bearer {self.access_token}",
                "accept": "application/json",
            }
        return {"accept": "application/json"}

    def _get_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get query parameters with API key if not using Bearer token."""
        base_params = params or {}
        if not self.access_token:
            base_params["api_key"] = self.api_key
        return base_params

    async def _request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make an authenticated request to the TMDb API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()
        query_params = self._get_params(params)

        try:
            response = await self._client.request(
                method, url, headers=headers, params=query_params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:  # noqa: S110
                pass
            error_message = error_data.get("status_message", str(e))
            raise TMDbAPIError(e.response.status_code, error_message) from e
        except httpx.RequestError as e:
            raise TMDbAPIError(0, f"Request failed: {str(e)}") from e

    async def search_movie(
        self,
        query: str,
        *,
        limit: int = 20,
        year: Optional[int] = None,
        primary_release_year: Optional[int] = None,
        include_adult: bool = False,
        region: Optional[str] = None,
        language: str = "en-US",
    ) -> list["MovieMedia"]:
        """Search for movies by title and return MovieMedia entries."""

        page = 1
        movies: list[MovieMedia] = []

        while len(movies) < limit:
            params: dict[str, Any] = {
                "query": query,
                "page": page,
                "include_adult": include_adult,
                "language": language,
            }
            if year is not None:
                params["year"] = year
            if primary_release_year is not None:
                params["primary_release_year"] = primary_release_year
            if region:
                params["region"] = region

            data = await self._request("GET", "search/movie", params)
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                parsed = self._parse_movie_search_result(item)
                movie = self._movie_media_from_search_result(parsed)
                movies.append(movie)
                if len(movies) >= limit:
                    break

            total_pages = data.get("total_pages") or 1
            if page >= total_pages:
                break
            page += 1

        return movies[:limit]

    async def get_movie_details(
        self,
        movie_id: int,
        *,
        language: str = "en-US",
        append_to_response: Optional[list[str]] = None,
    ) -> "MovieMedia":
        """Get detailed information about a specific movie.
        
        Args:
            movie_id: TMDb movie ID
            language: Language for results
            append_to_response: Additional data to append (e.g., ['videos', 'credits', 'images'])
            
        Returns:
            MovieMedia with metadata from TMDb (file fields use placeholders)
        """
        params: dict[str, Any] = {"language": language}
        if append_to_response:
            params["append_to_response"] = ",".join(append_to_response)

        data = await self._request("GET", f"movie/{movie_id}", params)

        # Parse genres
        genres = [
            TMDbGenre(id=g["id"], name=g["name"]) for g in data.get("genres", [])
        ]

        # Parse production companies
        companies = [
            TMDbProductionCompany(
                id=c["id"],
                name=c["name"],
                logo_path=c.get("logo_path"),
                origin_country=c.get("origin_country", ""),
            )
            for c in data.get("production_companies", [])
        ]

        # Parse production countries
        countries = [
            TMDbProductionCountry(
                iso_3166_1=c["iso_3166_1"],
                name=c["name"],
            )
            for c in data.get("production_countries", [])
        ]

        # Parse spoken languages
        languages = [
            TMDbSpokenLanguage(
                iso_639_1=lang["iso_639_1"],
                name=lang["name"],
                english_name=lang.get("english_name", lang["name"]),
            )
            for lang in data.get("spoken_languages", [])
        ]

        # Build TMDbMovie for internal use
        tmdb_movie = TMDbMovie(
            id=data["id"],
            title=data.get("title", ""),
            original_title=data.get("original_title", ""),
            tagline=data.get("tagline"),
            overview=data.get("overview"),
            release_date=data.get("release_date"),
            runtime=data.get("runtime"),
            status=data.get("status", ""),
            budget=data.get("budget", 0),
            revenue=data.get("revenue", 0),
            homepage=data.get("homepage"),
            imdb_id=data.get("imdb_id"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            popularity=data.get("popularity", 0.0),
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            adult=data.get("adult", False),
            original_language=data.get("original_language", ""),
            genres=genres,
            production_companies=companies,
            production_countries=countries,
            spoken_languages=languages,
            raw_data=data,
        )
        
        # Convert to MovieMedia with placeholder file fields
        return self.to_movie_media(
            tmdb_movie=tmdb_movie,
            file_hash="",  # Placeholder - will be set when file is ingested
            embedding_hash="",  # Placeholder - will be set when embeddings are generated
            path="",  # Placeholder - will be set when file is stored
            file_format=None,
        )

    async def search_tv(
        self,
        query: str,
        *,
        first_air_date_year: Optional[int] = None,
        page: int = 1,
        include_adult: bool = False,
        language: str = "en-US",
    ) -> list[TMDbTvSearchResult]:
        """Search for TV shows by name.
        
        Args:
            query: TV show name to search for
            first_air_date_year: Filter by first air date year
            page: Page number (1-based)
            include_adult: Include adult content in results
            language: Language for results (ISO 639-1 code with optional country)
            
        Returns:
            List of TV show search results
        """
        params: dict[str, Any] = {
            "query": query,
            "page": page,
            "include_adult": include_adult,
            "language": language,
        }
        if first_air_date_year is not None:
            params["first_air_date_year"] = first_air_date_year

        data = await self._request("GET", "search/tv", params)
        results = []
        
        for item in data.get("results", []):
            results.append(
                TMDbTvSearchResult(
                    id=item["id"],
                    name=item.get("name", ""),
                    original_name=item.get("original_name", ""),
                    first_air_date=item.get("first_air_date"),
                    overview=item.get("overview"),
                    poster_path=item.get("poster_path"),
                    backdrop_path=item.get("backdrop_path"),
                    popularity=item.get("popularity", 0.0),
                    vote_average=item.get("vote_average", 0.0),
                    vote_count=item.get("vote_count", 0),
                    origin_country=item.get("origin_country", []),
                    original_language=item.get("original_language", ""),
                    genre_ids=item.get("genre_ids", []),
                )
            )
        
        return results

    async def get_tv_details(
        self,
        tv_id: int,
        *,
        language: str = "en-US",
        append_to_response: Optional[list[str]] = None,
    ) -> "TvShowMedia":
        """Get detailed information about a specific TV show.
        
        Args:
            tv_id: TMDb TV show ID
            language: Language for results
            append_to_response: Additional data to append (e.g., ['credits', 'images', 'external_ids'])
            
        Returns:
            TvShowMedia with metadata from TMDb (file fields use placeholders)
        """
        params: dict[str, Any] = {"language": language}
        if append_to_response:
            params["append_to_response"] = ",".join(append_to_response)

        data = await self._request("GET", f"tv/{tv_id}", params)

        # Parse genres
        genres = [
            TMDbGenre(id=g["id"], name=g["name"]) for g in data.get("genres", [])
        ]

        # Parse production companies
        companies = [
            TMDbProductionCompany(
                id=c["id"],
                name=c["name"],
                logo_path=c.get("logo_path"),
                origin_country=c.get("origin_country", ""),
            )
            for c in data.get("production_companies", [])
        ]

        # Parse production countries
        countries = [
            TMDbProductionCountry(
                iso_3166_1=c["iso_3166_1"],
                name=c["name"],
            )
            for c in data.get("production_countries", [])
        ]

        # Parse spoken languages
        languages = [
            TMDbSpokenLanguage(
                iso_639_1=lang["iso_639_1"],
                name=lang["name"],
                english_name=lang.get("english_name", lang["name"]),
            )
            for lang in data.get("spoken_languages", [])
        ]

        # Build TMDbTvShow for internal use
        tmdb_tv = TMDbTvShow(
            id=data["id"],
            name=data.get("name", ""),
            original_name=data.get("original_name", ""),
            tagline=data.get("tagline"),
            overview=data.get("overview"),
            first_air_date=data.get("first_air_date"),
            last_air_date=data.get("last_air_date"),
            status=data.get("status", ""),
            type=data.get("type", ""),
            number_of_seasons=data.get("number_of_seasons", 0),
            number_of_episodes=data.get("number_of_episodes", 0),
            homepage=data.get("homepage"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            popularity=data.get("popularity", 0.0),
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            original_language=data.get("original_language", ""),
            origin_country=data.get("origin_country", []),
            genres=genres,
            production_companies=companies,
            production_countries=countries,
            spoken_languages=languages,
            networks=data.get("networks", []),
            created_by=data.get("created_by", []),
            raw_data=data,
        )
        
        # Convert to TvShowMedia with placeholder file fields
        return self.to_tv_show_media(
            tmdb_tv=tmdb_tv,
            file_hash="",  # Placeholder - will be set when file is ingested
            embedding_hash="",  # Placeholder - will be set when embeddings are generated
            path="",  # Placeholder - will be set when file is stored
            file_format=None,
        )

    def get_image_url(
        self, path: Optional[str], size: str = "original"
    ) -> Optional[str]:
        """Construct full image URL from TMDb image path.
        
        Args:
            path: Image path from TMDb (e.g., poster_path, backdrop_path)
            size: Image size (w92, w154, w185, w342, w500, w780, original for posters)
                  (w300, w780, w1280, original for backdrops)
        
        Returns:
            Full image URL or None if path is None
        """
        if not path:
            return None
        return f"{self.IMAGE_BASE_URL}{size}{path}"

    def _parse_movie_search_result(self, item: dict[str, Any]) -> TMDbSearchResult:
        return TMDbSearchResult(
            id=item.get("id"),
            title=item.get("title", ""),
            original_title=item.get("original_title", ""),
            release_date=item.get("release_date"),
            overview=item.get("overview"),
            poster_path=item.get("poster_path"),
            backdrop_path=item.get("backdrop_path"),
            popularity=item.get("popularity", 0.0),
            vote_average=item.get("vote_average", 0.0),
            vote_count=item.get("vote_count", 0),
            adult=item.get("adult", False),
            original_language=item.get("original_language", ""),
            genre_ids=item.get("genre_ids", []) or [],
        )

    def _movie_media_from_search_result(self, result: TMDbSearchResult) -> "MovieMedia":
        from domain.media.base import ImageMetadata
        from domain.media.movies import MovieMedia

        release_date = None
        year = None
        if result.release_date:
            try:
                release_date = datetime.fromisoformat(result.release_date)
                year = release_date.year
            except (ValueError, TypeError):
                logger.debug("Unable to parse release date %s", result.release_date)

        poster = None
        poster_url = self.get_image_url(result.poster_path, size="w500")
        if poster_url:
            poster = ImageMetadata(file_path=poster_url, width=None, height=None, aspect_ratio=None)

        backdrop = None
        backdrop_url = self.get_image_url(result.backdrop_path, size="original")
        if backdrop_url:
            backdrop = ImageMetadata(file_path=backdrop_url, width=None, height=None, aspect_ratio=None)

        languages = [result.original_language] if result.original_language else None

        return MovieMedia(
            file_hash=None,
            embedding_hash=None,
            path=None,
            media_type="movie",
            format=None,
            title=result.title or result.original_title,
            tagline=None,
            overview=result.overview,
            release_date=release_date,
            year=year,
            runtime_min=None,
            genres=None,
            languages=languages,
            vote_average=result.vote_average,
            vote_count=result.vote_count,
            cast=None,
            rating="adult" if result.adult else None,
            poster=poster,
            backdrop=backdrop,
            catalog_source="tmdb",
            catalog_id=str(result.id),
            catalog_score=result.popularity,
            catalog_downloads=None,
        )

    def to_movie_media(
        self,
        tmdb_movie: TMDbMovie,
        file_hash: str,
        embedding_hash: str,
        path: str,
        file_format: Optional[str] = None,
    ) -> "MovieMedia":
        """Convert TMDbMovie to MovieMedia domain type.
        
        Args:
            tmdb_movie: TMDb movie data
            file_hash: File hash for the media
            embedding_hash: Embedding vector hash
            path: File path
            file_format: Optional file format/extension
            
        Returns:
            MovieMedia instance with coerced types
        """
        from domain.media.base import ImageMetadata
        from domain.media.movies import MovieMedia
        
        # Parse release date
        release_date = None
        year = None
        if tmdb_movie.release_date:
            try:
                release_date = datetime.fromisoformat(tmdb_movie.release_date)
                year = release_date.year
            except (ValueError, AttributeError):
                logger.warning(f"Invalid release date format: {tmdb_movie.release_date}")
        
        # Extract cast names
        cast_names = None
        if "credits" in tmdb_movie.raw_data:
            credits = tmdb_movie.raw_data["credits"]
            cast_data = credits.get("cast", [])[:20]  # Top 20 cast members
            if cast_data:
                cast_names = [member.get("name") for member in cast_data if member.get("name")]
        
        # Extract genres
        genres = None
        if tmdb_movie.genres:
            genres = [g.name for g in tmdb_movie.genres]
        
        # Extract languages
        languages = None
        if tmdb_movie.spoken_languages:
            languages = [lang.english_name for lang in tmdb_movie.spoken_languages]
        
        # Create poster and backdrop metadata
        poster = None
        if tmdb_movie.poster_path:
            poster = ImageMetadata(
                file_path=self.get_image_url(tmdb_movie.poster_path, size="w500") or tmdb_movie.poster_path,
                width=None,
                height=None,
                aspect_ratio=None,
            )
        
        backdrop = None
        if tmdb_movie.backdrop_path:
            backdrop = ImageMetadata(
                file_path=self.get_image_url(tmdb_movie.backdrop_path, size="original") or tmdb_movie.backdrop_path,
                width=None,
                height=None,
                aspect_ratio=None,
            )
        
        return MovieMedia(
            file_hash=file_hash,
            embedding_hash=embedding_hash,
            path=path,
            media_type="movie",
            format=file_format,
            title=tmdb_movie.title,
            tagline=tmdb_movie.tagline,
            overview=tmdb_movie.overview,
            release_date=release_date,
            year=year,
            runtime_min=tmdb_movie.runtime,
            genres=genres,
            languages=languages,
            vote_average=tmdb_movie.vote_average,
            vote_count=tmdb_movie.vote_count,
            cast=cast_names,
            rating="adult" if tmdb_movie.adult else None,
            poster=poster,
            backdrop=backdrop,
            catalog_source="tmdb",
            catalog_id=str(tmdb_movie.id),
            catalog_score=tmdb_movie.popularity,
            catalog_downloads=None,
        )
    
    def to_tv_show_media(
        self,
        tmdb_tv: TMDbTvShow,
        file_hash: str,
        embedding_hash: str,
        path: str,
        file_format: Optional[str] = None,
    ) -> "TvShowMedia":
        """Convert TMDbTvShow to TvShowMedia domain type.
        
        Args:
            tmdb_tv: TMDb TV show data
            file_hash: File hash for the media
            embedding_hash: Embedding vector hash
            path: File path
            file_format: Optional file format/extension
            
        Returns:
            TvShowMedia instance with coerced types
        """
        from domain.media.base import ImageMetadata
        from domain.media.tv import TvShowMedia
        
        # Parse air dates
        first_air_date = None
        last_air_date = None
        if tmdb_tv.first_air_date:
            try:
                first_air_date = datetime.fromisoformat(tmdb_tv.first_air_date)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid first air date format: {tmdb_tv.first_air_date}")
        
        if tmdb_tv.last_air_date:
            try:
                last_air_date = datetime.fromisoformat(tmdb_tv.last_air_date)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid last air date format: {tmdb_tv.last_air_date}")
        
        # Extract cast names
        cast_names = None
        if "credits" in tmdb_tv.raw_data:
            credits = tmdb_tv.raw_data["credits"]
            cast_data = credits.get("cast", [])[:20]  # Top 20 cast members
            if cast_data:
                cast_names = [member.get("name") for member in cast_data if member.get("name")]
        
        # Extract genres
        genres = None
        if tmdb_tv.genres:
            genres = [g.name for g in tmdb_tv.genres]
        
        # Extract languages
        languages = None
        if tmdb_tv.spoken_languages:
            languages = [lang.english_name for lang in tmdb_tv.spoken_languages]
        
        # Create poster and backdrop metadata
        poster = None
        if tmdb_tv.poster_path:
            poster = ImageMetadata(
                file_path=self.get_image_url(tmdb_tv.poster_path, size="w500") or tmdb_tv.poster_path,
                width=None,
                height=None,
                aspect_ratio=None,
            )
        
        backdrop = None
        if tmdb_tv.backdrop_path:
            backdrop = ImageMetadata(
                file_path=self.get_image_url(tmdb_tv.backdrop_path, size="original") or tmdb_tv.backdrop_path,
                width=None,
                height=None,
                aspect_ratio=None,
            )
        
        return TvShowMedia(
            file_hash=file_hash,
            embedding_hash=embedding_hash,
            path=path,
            media_type="tv",
            format=file_format,
            name=tmdb_tv.name,
            overview=tmdb_tv.overview,
            type=tmdb_tv.type,
            status=tmdb_tv.status,
            first_air_date=first_air_date,
            last_air_date=last_air_date,
            number_of_seasons=tmdb_tv.number_of_seasons,
            number_of_episodes=tmdb_tv.number_of_episodes,
            genres=genres,
            languages=languages,
            vote_average=tmdb_tv.vote_average,
            vote_count=tmdb_tv.vote_count,
            cast=cast_names,
            seasons=None,  # Would need additional API calls to populate
            poster=poster,
            backdrop=backdrop,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> TMDbClient:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()


def get_tmdb_client(api_key: str, access_token: Optional[str] = None) -> TMDbClient:
    """Factory function to create a TMDb client instance.
    
    Args:
        api_key: TMDb API key
        access_token: Optional Bearer token (preferred authentication method)
        
    Returns:
        Configured TMDb client
    """
    return TMDbClient(api_key=api_key, access_token=access_token)
