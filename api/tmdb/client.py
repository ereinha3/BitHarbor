from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


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

    def __init__(self, api_key: str, access_token: Optional[str] = None) -> None:
        """Initialize TMDb client.
        
        Args:
            api_key: TMDb API key (v3 auth)
            access_token: TMDb API Read Access Token (Bearer token, preferred)
        """
        self.api_key = api_key
        self.access_token = access_token
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
        year: Optional[int] = None,
        primary_release_year: Optional[int] = None,
        page: int = 1,
        include_adult: bool = False,
        region: Optional[str] = None,
        language: str = "en-US",
    ) -> list[TMDbSearchResult]:
        """Search for movies by title.
        
        Args:
            query: Movie title to search for
            year: Filter by release year
            primary_release_year: Filter by primary release year
            page: Page number (1-based)
            include_adult: Include adult content in results
            region: ISO 3166-1 code to filter release dates
            language: Language for results (ISO 639-1 code with optional country)
            
        Returns:
            List of search results
        """
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
        results = []
        
        for item in data.get("results", []):
            results.append(
                TMDbSearchResult(
                    id=item["id"],
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
                    genre_ids=item.get("genre_ids", []),
                )
            )
        
        return results

    async def get_movie_details(
        self,
        movie_id: int,
        *,
        language: str = "en-US",
        append_to_response: Optional[list[str]] = None,
    ) -> TMDbMovie:
        """Get detailed information about a specific movie.
        
        Args:
            movie_id: TMDb movie ID
            language: Language for results
            append_to_response: Additional data to append (e.g., ['videos', 'credits', 'images'])
            
        Returns:
            Detailed movie information
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

        return TMDbMovie(
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
            raw_data=data,  # Store complete response for additional fields
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
