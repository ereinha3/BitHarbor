"""Lightweight text search service for real-time semantic search.

This service combines Sentence-BERT embeddings with DiskANN vector search
to provide fast, as-you-type semantic search capabilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ann.service import AnnResult, AnnService, get_ann_service
from infrastructure.embedding import get_sentence_bert_service, SentenceBertService

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from text search containing media ID and similarity score."""
    media_id: str
    score: float
    vector_hash: str


class TextSearchService:
    """Lightweight service for real-time semantic text search.
    
    This service is optimized for fast, as-you-type search experiences:
    - Uses lightweight Sentence-BERT (384-dim) instead of heavy ImageBind (1024-dim)
    - Single-threaded embedding generation (queries are small)
    - Efficient vector search via DiskANN
    - No database I/O during embedding step
    
    Typical query latency: 10-30ms on CPU, 5-10ms on GPU
    """
    
    def __init__(
        self,
        embedding_service: Optional[SentenceBertService] = None,
        ann_service: Optional[AnnService] = None,
    ) -> None:
        """Initialize the text search service.
        
        Args:
            embedding_service: Optional Sentence-BERT service (creates if None)
            ann_service: Optional ANN service (creates if None)
        """
        self.embedding_service = embedding_service or get_sentence_bert_service()
        self.ann_service = ann_service or get_ann_service()
        
        # Validate embedding dimensions match ANN index
        embedding_dim = self.embedding_service.get_embedding_dimension()
        ann_dim = self.ann_service.settings.embedding.dim
        
        if embedding_dim != ann_dim:
            logger.warning(
                f"Dimension mismatch: SentenceBERT={embedding_dim}, ANN={ann_dim}. "
                f"Search may not work correctly. Consider updating ANN index dimension."
            )
    
    def search(
        self,
        query: str,
        k: int = 20,
        min_score: float = 0.0,
    ) -> list[AnnResult]:
        """Search for media using semantic text similarity (synchronous).
        
        This method is optimized for real-time search and does not require
        a database session. Use resolve_results() separately to get media IDs.
        
        Args:
            query: Search query text
            k: Number of results to return
            min_score: Minimum similarity score threshold (0.0-1.0)
            
        Returns:
            List of AnnResult with row_id and score (media_id will be None)
        """
        if not query or not query.strip():
            return []
        
        # Encode query to vector (fast - single text)
        result = self.embedding_service.encode(query.strip())
        query_vector = result.vector
        
        # Search vector index (fast - no I/O)
        results = self.ann_service.search(query_vector, k=k)
        
        # Filter by minimum score
        if min_score > 0.0:
            results = [r for r in results if r.score >= min_score]
        
        return results
    
    async def search_with_media_ids(
        self,
        session: AsyncSession,
        query: str,
        k: int = 20,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for media and resolve to media IDs (requires database).
        
        Use this when you need the actual media_id values, not just scores.
        For real-time as-you-type search, prefer using search() + resolve_results()
        to batch the database lookups.
        
        Args:
            session: Database session for resolving media IDs
            query: Search query text
            k: Number of results to return
            min_score: Minimum similarity score threshold (0.0-1.0)
            
        Returns:
            List of SearchResult with media_id, score, and vector_hash
        """
        # Get raw search results
        raw_results = self.search(query, k=k, min_score=min_score)
        
        if not raw_results:
            return []
        
        # Resolve media IDs from database
        resolved = await self.ann_service.resolve_media(session, raw_results)
        
        # Convert to SearchResult format
        search_results = []
        for result in resolved:
            if result.media_id:  # Only include results with valid media_id
                search_results.append(
                    SearchResult(
                        media_id=result.media_id,
                        score=result.score,
                        vector_hash=result.vector_hash or "",
                    )
                )
        
        return search_results
    
    async def resolve_results(
        self,
        session: AsyncSession,
        ann_results: list[AnnResult],
    ) -> list[SearchResult]:
        """Resolve ANN results to media IDs (batch operation).
        
        Use this to batch multiple search result resolutions together,
        useful for debounced as-you-type search.
        
        Args:
            session: Database session
            ann_results: Raw ANN search results
            
        Returns:
            List of SearchResult with resolved media_id values
        """
        if not ann_results:
            return []
        
        resolved = await self.ann_service.resolve_media(session, ann_results)
        
        search_results = []
        for result in resolved:
            if result.media_id:
                search_results.append(
                    SearchResult(
                        media_id=result.media_id,
                        score=result.score,
                        vector_hash=result.vector_hash or "",
                    )
                )
        
        return search_results
    
    def encode_for_indexing(self, text: str) -> tuple[np.ndarray, str]:
        """Encode text for adding to the search index.
        
        Use this when ingesting new media to generate embeddings for indexing.
        
        Args:
            text: Text to encode (e.g., movie title + description)
            
        Returns:
            Tuple of (vector, vector_hash)
        """
        result = self.embedding_service.encode(text)
        return result.vector, result.vector_hash
    
    def encode_batch_for_indexing(self, texts: list[str]) -> list[tuple[np.ndarray, str]]:
        """Encode multiple texts for batch indexing.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of (vector, vector_hash) tuples
        """
        results = self.embedding_service.encode_batch(texts)
        return [(r.vector, r.vector_hash) for r in results]


# Singleton instance
_text_search_service: TextSearchService | None = None


def get_text_search_service() -> TextSearchService:
    """Get or create the text search service singleton.
    
    Returns:
        TextSearchService instance
    """
    global _text_search_service
    if _text_search_service is None:
        _text_search_service = TextSearchService()
    return _text_search_service
