"""Lightweight text embedding service using Sentence-BERT.

This service provides fast, high-quality text embeddings optimized for semantic search.
Uses the all-MiniLM-L6-v2 model (384 dimensions) which is much lighter than ImageBind
while maintaining excellent performance for text similarity tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from app.settings import get_settings
from utils.hashing import canonicalize_vector

logger = logging.getLogger(__name__)


def _resolve_device(device_pref: str) -> torch.device:
    """Resolve device preference to actual torch device.
    
    Args:
        device_pref: Device preference ("cuda", "cpu", or "auto")
        
    Returns:
        torch.device instance
    """
    if device_pref == "cuda":
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA memory available: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        else:
            device = torch.device("cpu")
            logger.warning("CUDA requested but not available, falling back to CPU")
        return device
    
    if device_pref == "cpu":
        logger.info("Using CPU device (as requested)")
        return torch.device("cpu")
    
    # auto - detect best available device
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"Auto-detected CUDA device: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA memory available: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        device = torch.device("cpu")
        logger.info("CUDA not available, using CPU device")
    
    return device


@dataclass
class TextEmbeddingResult:
    """Result of text embedding containing vector and hash."""
    vector: np.ndarray
    vector_hash: str


class SentenceBertService:
    """Lightweight text embedding service using Sentence-BERT.
    
    This service uses the all-MiniLM-L6-v2 model which produces 384-dimensional
    embeddings optimized for semantic similarity. It's significantly faster and
    lighter than ImageBind while maintaining excellent quality for text search.
    
    Features:
    - 384-dimensional embeddings (vs ImageBind's 1024)
    - ~10x faster inference than BERT base
    - Optimized for semantic similarity tasks
    - Batch processing support
    - Automatic normalization and canonicalization
    """
    
    # Model dimensions for validation
    EXPECTED_DIM = 384
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "auto",
        round_eps: float = 1e-6,
    ) -> None:
        """Initialize the Sentence-BERT service.
        
        Args:
            model_name: Name of the sentence-transformers model
                       Options:
                       - "all-MiniLM-L6-v2" (default): 384 dim, fastest, good quality
                       - "all-mpnet-base-v2": 768 dim, slower, best quality
                       - "all-MiniLM-L12-v2": 384 dim, balanced speed/quality
            device: Device preference ("cuda", "cpu", or "auto")
            round_eps: Epsilon for vector rounding (for deterministic hashing)
        """
        settings = get_settings()
        self.model_name = model_name
        self.device = _resolve_device(device)
        self.round_eps = round_eps
        
        # Load the model
        logger.info(f"Loading Sentence-BERT model: {model_name}")
        self.model = SentenceTransformer(model_name, device=str(self.device))
        self.model.eval()
        logger.info(f"Model loaded successfully on {self.device}")
        
        # Validate dimensions
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")
        if model_name == "all-MiniLM-L6-v2" and self.embedding_dim != self.EXPECTED_DIM:
            raise ValueError(
                f"Expected {self.EXPECTED_DIM} dimensions for {model_name}, "
                f"got {self.embedding_dim}"
            )
    
    def _canonicalize(self, vector: np.ndarray) -> TextEmbeddingResult:
        """Canonicalize vector: normalize, round, and hash.
        
        Args:
            vector: Raw embedding vector
            
        Returns:
            TextEmbeddingResult with canonical vector and hash
        """
        vec = np.asarray(vector, dtype=np.float32)
        canonical_vec, vec_hash = canonicalize_vector(vec, round_eps=self.round_eps)
        return TextEmbeddingResult(vector=canonical_vec, vector_hash=vec_hash)
    
    def encode(self, text: str) -> TextEmbeddingResult:
        """Encode a single text string into an embedding.
        
        Args:
            text: Text string to embed
            
        Returns:
            TextEmbeddingResult with vector and hash
        """
        results = self.encode_batch([text])
        return results[0]
    
    def encode_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
    ) -> list[TextEmbeddingResult]:
        """Encode a batch of texts into embeddings.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once (for large batches)
            
        Returns:
            List of TextEmbeddingResult with vectors and hashes
        """
        if not texts:
            return []
        
        all_results = []
        
        # Process in batches if needed
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Encode texts - model handles batching and normalization
            with torch.no_grad():
                embeddings = self.model.encode(
                    list(batch),
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # L2 normalize for cosine similarity
                    show_progress_bar=False,
                )
            
            # Canonicalize each embedding
            batch_results = [self._canonicalize(vec) for vec in embeddings]
            all_results.extend(batch_results)
        
        return all_results
    
    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings produced by this model.
        
        Returns:
            Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        return self.embedding_dim


# Singleton instance
_sentence_bert_service: SentenceBertService | None = None


def get_sentence_bert_service(
    model_name: str = "all-MiniLM-L6-v2",
    device: str = "auto",
) -> SentenceBertService:
    """Get or create the Sentence-BERT service singleton.
    
    Args:
        model_name: Name of the sentence-transformers model
        device: Device preference ("cuda", "cpu", or "auto")
        
    Returns:
        SentenceBertService instance
    """
    global _sentence_bert_service
    if _sentence_bert_service is None:
        _sentence_bert_service = SentenceBertService(
            model_name=model_name,
            device=device,
        )
    return _sentence_bert_service
