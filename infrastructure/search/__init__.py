"""Infrastructure for semantic search."""

from .search import SearchResult, TextSearchService, get_text_search_service

__all__ = [
    "SearchResult",
    "TextSearchService",
    "get_text_search_service",
]
