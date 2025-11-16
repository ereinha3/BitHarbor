from __future__ import annotations
from functools import cached_property
from .tmdb.client import TMDbClient


tmdb = TMDbClient()

class ABCMetadata(ABC):
    @abstractmethod
    def search(self, query: str) -> list[BaseMedia]:
        pass


class MovieMetadata(ABCMetadata):
    def search(self, query: str) -> list[BaseMedia]:
        return tmdb.search_movie(query=query)

class TVMetadata(ABCMetadata):
    def search(self, query: str) -> list[BaseMedia]:
        return tmdb.search_tv(query=query)

class MusicMetadata(ABCMetadata):

class MetadataRegistry:

    @cached_property
    def movies():
        return MovieMetadata()
    
    @cached_property
    def tv():
        return {
            "tmdb": TMDbMetadata(),
        }
    
    @cached_property
    def music():
        return {
            "spotify": SpotifyMetadata(),
        }