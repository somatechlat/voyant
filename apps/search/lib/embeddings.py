"""
Embedding Extraction Module

Extract embeddings from unstructured text and images.

Features:
- Text embedding via TF-IDF (lightweight, no external models required).
- Simple character-based embedder for pipeline testing.
- Batch processing with L2 normalisation.
- Cosine similarity and Euclidean distance for similarity search.
- Variance-based dimensionality reduction.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class EmbeddingModel(str, Enum):
    """Available embedding models."""

    SIMPLE = "simple"  # Character-based (for testing)
    TFIDF = "tfidf"  # TF-IDF (lightweight)
    DENSE = "dense"  # Deterministic 1536-dim dense embeddings
    SPARSE = "sparse"  # Sparse BM25 vectors


@dataclass
class EmbeddingResult:
    """Result of embedding extraction."""

    embeddings: List[List[float]]  # List of vectors
    model: str
    dimensions: int
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "count": self.count,
            "embeddings": self.embeddings,
        }


@dataclass
class SimilarityResult:
    """Result of similarity calculation."""

    similarity: float  # 0 to 1 (cosine similarity)
    distance: float  # Euclidean distance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "similarity": round(self.similarity, 6),
            "distance": round(self.distance, 6),
        }


# =============================================================================
# Embedding Extractors
# =============================================================================


class EmbeddingExtractor(ABC):
    """Base class for embedding extractors."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    @abstractmethod
    def embed(self, texts: List[str]) -> EmbeddingResult:
        """Embed a list of texts."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class SimpleEmbedder(EmbeddingExtractor):
    """
    Character-frequency embedder for test pipelines only.

    Raises RuntimeError if instantiated outside of test mode.
    """

    def __init__(self, dimensions: int = 64):
        from apps.core.config import get_settings
        env = get_settings().env
        if env != "test":
            raise RuntimeError(
                "SimpleEmbedder is a test-only implementation. "
                "Use 'tfidf' or 'dense' for production embeddings."
            )
        super().__init__(dimensions)
        self.chars = "abcdefghijklmnopqrstuvwxyz0123456789 .,!?-"

    @property
    def model_name(self) -> str:
        return "simple"

    def embed(self, texts: List[str]) -> EmbeddingResult:
        embeddings = []

        for text in texts:
            text_lower = text.lower()[:10000]  # Security: limit length

            # Character frequency vector
            vector = [0.0] * min(self.dimensions, len(self.chars))
            for i, char in enumerate(self.chars[: self.dimensions]):
                vector[i] = text_lower.count(char) / max(len(text_lower), 1)

            # Pad to dimensions
            while len(vector) < self.dimensions:
                vector.append(0.0)

            # Normalize
            vector = self._normalize(vector)
            embeddings.append(vector)

        return EmbeddingResult(
            embeddings=embeddings,
            model=self.model_name,
            dimensions=self.dimensions,
            count=len(texts),
        )

    def _normalize(self, vector: List[float]) -> List[float]:
        """L2 normalize a vector."""
        magnitude = math.sqrt(sum(x**2 for x in vector))
        if magnitude == 0:
            return vector
        return [x / magnitude for x in vector]


class TFIDFEmbedder(EmbeddingExtractor):
    """
    TF-IDF based embedder.

    Lightweight embedding using term frequency-inverse document frequency.
    """

    def __init__(self, dimensions: int = 128, max_features: int = 1000):
        super().__init__(dimensions)
        self.max_features = max_features
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}

    @property
    def model_name(self) -> str:
        return "tfidf"

    def embed(self, texts: List[str]) -> EmbeddingResult:
        # Build vocabulary
        self._build_vocabulary(texts)

        embeddings = []
        for text in texts:
            vector = self._text_to_tfidf(text)
            embeddings.append(vector)

        return EmbeddingResult(
            embeddings=embeddings,
            model=self.model_name,
            dimensions=self.dimensions,
            count=len(texts),
        )

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        text = text.lower()[:10000]  # Security: limit length
        # Simple word split
        words = []
        current = []
        for char in text:
            if char.isalnum():
                current.append(char)
            elif current:
                words.append("".join(current))
                current = []
        if current:
            words.append("".join(current))
        return words

    def _build_vocabulary(self, texts: List[str]):
        """Build vocabulary and IDF from texts."""
        doc_freq: Dict[str, int] = {}
        n_docs = len(texts)

        for text in texts:
            tokens = set(self._tokenize(text))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # Sort by frequency and take top features
        sorted_terms = sorted(doc_freq.items(), key=lambda x: x[1], reverse=True)

        self._vocabulary = {}
        self._idf = {}
        for i, (term, freq) in enumerate(sorted_terms[: self.max_features]):
            if i >= self.dimensions:
                break
            self._vocabulary[term] = i
            self._idf[term] = math.log((n_docs + 1) / (freq + 1)) + 1

    def _text_to_tfidf(self, text: str) -> List[float]:
        """Convert text to TF-IDF vector."""
        tokens = self._tokenize(text)

        # Term frequency
        tf: Dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        # Build vector
        vector = [0.0] * self.dimensions
        max_tf = max(tf.values()) if tf else 1

        for term, freq in tf.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                if idx < self.dimensions:
                    # Normalized TF-IDF
                    tf_norm = freq / max_tf
                    vector[idx] = tf_norm * self._idf.get(term, 1)

        # L2 normalize
        magnitude = math.sqrt(sum(x**2 for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector


class DenseEmbedder(EmbeddingExtractor):
    """
    Deterministic 1536-dim dense embedder using hash-based random projection.

    Generates stable embeddings suitable for Milvus dense vector fields
    without requiring external model APIs. Uses SHA-256 hashing for
    reproducibility across process restarts.
    """

    def __init__(self, dimensions: int = 1536):
        super().__init__(dimensions)

    @property
    def model_name(self) -> str:
        return "dense"

    def embed(self, texts: List[str]) -> EmbeddingResult:
        embeddings = []
        for text in texts:
            vector = self._embed_text(text)
            embeddings.append(vector)

        return EmbeddingResult(
            embeddings=embeddings,
            model=self.model_name,
            dimensions=self.dimensions,
            count=len(texts),
        )

    def _embed_text(self, text: str) -> List[float]:
        """Embed a single text into a dense vector."""
        tokens = self._tokenize(text)
        vec = [0.0] * self.dimensions
        if not tokens:
            return vec

        for token in tokens:
            h = hashlib.sha256(token.encode("utf-8")).digest()
            # Use chunks of the hash to drive a deterministic pseudo-random
            # update across all dimensions.
            rng = random.Random(int.from_bytes(h[:8], "big"))
            for i in range(self.dimensions):
                vec[i] += rng.gauss(0.0, 1.0)

        # Mean pooling + L2 normalisation
        n = len(tokens)
        vec = [x / n for x in vec]
        magnitude = math.sqrt(sum(x**2 for x in vec))
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        return vec

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        text = text.lower()[:10000]
        words = []
        current = []
        for char in text:
            if char.isalnum():
                current.append(char)
            elif current:
                words.append("".join(current))
                current = []
        if current:
            words.append("".join(current))
        return words


class SparseEmbedder:
    """
    Sparse BM25-like embedder for Milvus sparse vector fields.

    Produces dictionary-formatted sparse vectors where keys are
    uint32 term hashes and values are BM25-normalised weights.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    @property
    def model_name(self) -> str:
        return "sparse"

    def embed(self, texts: List[str]) -> List[Dict[int, float]]:
        """Embed a list of texts into sparse vectors."""
        return [self._embed_text(t) for t in texts]

    def _embed_text(self, text: str) -> Dict[int, float]:
        """Embed a single text into a sparse BM25 vector."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        term_counts = Counter(tokens)
        doc_len = len(tokens)
        avg_len = doc_len  # Single-doc average for simplicity

        sparse: Dict[int, float] = {}
        for term, freq in term_counts.items():
            idx = self._term_to_index(term)
            # Simplified BM25 without corpus IDF (using constant IDF=1)
            denom = freq + self.k1 * (1 - self.b + self.b * (doc_len / avg_len))
            weight = ((self.k1 + 1) * freq) / max(denom, 1e-6)
            sparse[idx] = sparse.get(idx, 0.0) + weight

        # L2 normalise sparse values
        magnitude = math.sqrt(sum(v**2 for v in sparse.values()))
        if magnitude > 0:
            sparse = {k: v / magnitude for k, v in sparse.items()}
        return sparse

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        text = text.lower()[:10000]
        words = []
        current = []
        for char in text:
            if char.isalnum():
                current.append(char)
            elif current:
                words.append("".join(current))
                current = []
        if current:
            words.append("".join(current))
        return words

    def _term_to_index(self, term: str) -> int:
        """Map a term to a deterministic uint32 index."""
        h = hashlib.sha256(term.encode("utf-8")).hexdigest()
        return int(h, 16) % (2**32 - 1)


# =============================================================================
# Similarity Functions
# =============================================================================


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two equal-length vectors."""
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimensions")

    dot_product = sum(a[i] * b[i] for i in range(len(a)))
    magnitude_a = math.sqrt(sum(x**2 for x in a))
    magnitude_b = math.sqrt(sum(x**2 for x in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """Calculate Euclidean distance between two vectors."""
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimensions")

    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))


def calculate_similarity(a: List[float], b: List[float]) -> SimilarityResult:
    """
    Calculate similarity between two embedding vectors.

    Returns both cosine similarity (0-1) and Euclidean distance.
    """
    return SimilarityResult(
        similarity=cosine_similarity(a, b),
        distance=euclidean_distance(a, b),
    )


# =============================================================================
# Dimensionality Reduction (Simple PCA-like)
# =============================================================================


def reduce_dimensions(
    embeddings: List[List[float]],
    target_dims: int = 2,
) -> List[List[float]]:
    """
    Simple dimensionality reduction using variance-based projection.

    Not a full PCA - just takes highest variance dimensions.
    For production, use sklearn.decomposition.PCA.
    """
    if not embeddings or target_dims >= len(embeddings[0]):
        return embeddings

    n_dims = len(embeddings[0])
    n_samples = len(embeddings)

    # Calculate variance per dimension
    variances = []
    for dim in range(n_dims):
        values = [emb[dim] for emb in embeddings]
        mean = sum(values) / n_samples
        variance = sum((v - mean) ** 2 for v in values) / n_samples
        variances.append((dim, variance))

    # Sort by variance and take top dimensions
    variances.sort(key=lambda x: x[1], reverse=True)
    top_dims = [v[0] for v in variances[:target_dims]]

    # Project to top dimensions
    reduced = []
    for emb in embeddings:
        reduced.append([emb[dim] for dim in top_dims])

    return reduced


# =============================================================================
# Main API
# =============================================================================

_EMBEDDERS = {
    "simple": SimpleEmbedder,
    "tfidf": TFIDFEmbedder,
    "dense": DenseEmbedder,
}


def embed_texts(
    texts: List[str],
    model: str = "tfidf",
    dimensions: int = 64,
) -> EmbeddingResult:
    """
    Embed a list of texts.

    Args:
        texts: List of text strings
        model: Embedding model ("simple", "tfidf")
        dimensions: Output dimensions

    Returns:
        EmbeddingResult with embedding vectors
    """
    if model not in _EMBEDDERS:
        raise ValueError(
            f"Unknown model: {model}. Available: {list(_EMBEDDERS.keys())}"
        )

    embedder = _EMBEDDERS[model](dimensions=dimensions)
    return embedder.embed(texts)


def get_available_models() -> List[str]:
    """Get list of available embedding models."""
    return list(_EMBEDDERS.keys())


def get_embedding_extractor(
    model: str = "tfidf", dimensions: int = 64
) -> EmbeddingExtractor:
    """
    Get an embedding extractor instance.

    Args:
        model: Model name ("simple", "tfidf", "dense")
        dimensions: Output dimensions (ignored for "dense" which is fixed at 1536)

    Returns:
        EmbeddingExtractor instance
    """
    if model not in _EMBEDDERS:
        raise ValueError(
            f"Unknown model: {model}. Available: {list(_EMBEDDERS.keys())}"
        )

    if model == "dense":
        return _EMBEDDERS[model](dimensions=1536)
    return _EMBEDDERS[model](dimensions=dimensions)


def get_sparse_embedder() -> SparseEmbedder:
    """Get a sparse BM25 embedder instance."""
    return SparseEmbedder()


def find_similar(
    query_embedding: List[float],
    corpus_embeddings: List[List[float]],
    top_k: int = 5,
) -> List[Tuple[int, float]]:
    """
    Find most similar embeddings in a corpus.

    Returns list of (index, similarity) tuples.
    """
    similarities = []
    for i, emb in enumerate(corpus_embeddings):
        sim = cosine_similarity(query_embedding, emb)
        similarities.append((i, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]
