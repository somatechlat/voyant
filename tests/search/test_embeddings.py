"""
Unit tests for deterministic embedding extractors.

No external models required — all embedders are hash-based and reproducible.
"""

import math

import pytest

from apps.search.lib.embeddings import (
    DenseEmbedder,
    EmbeddingResult,
    SparseEmbedder,
    get_embedding_extractor,
    get_sparse_embedder,
)


class TestDenseEmbedder:
    """Tests for the deterministic 1536-dim dense embedder."""

    def test_dimensions_fixed_at_1536(self):
        extractor = DenseEmbedder(dimensions=1536)
        result = extractor.embed(["hello world"])
        assert len(result.embeddings) == 1
        assert len(result.embeddings[0]) == 1536
        assert result.dimensions == 1536

    def test_reproducibility(self):
        """Same text must produce identical vectors across calls."""
        extractor = DenseEmbedder()
        r1 = extractor.embed(["temporal workflow engine"])
        r2 = extractor.embed(["temporal workflow engine"])
        assert r1.embeddings[0] == r2.embeddings[0]

    def test_different_texts_different_vectors(self):
        extractor = DenseEmbedder()
        r1 = extractor.embed(["hello"])
        r2 = extractor.embed(["world"])
        assert r1.embeddings[0] != r2.embeddings[0]

    def test_l2_normalised(self):
        extractor = DenseEmbedder()
        result = extractor.embed(["normalisation check"])
        vec = result.embeddings[0]
        magnitude = math.sqrt(sum(x * x for x in vec))
        assert pytest.approx(magnitude, abs=1e-6) == 1.0

    def test_empty_text_returns_zero_vector(self):
        extractor = DenseEmbedder()
        result = extractor.embed([""])
        assert all(x == 0.0 for x in result.embeddings[0])

    def test_model_name(self):
        assert DenseEmbedder().model_name == "dense"

    def test_get_embedding_extractor_factory(self):
        ext = get_embedding_extractor("dense", dimensions=1536)
        assert isinstance(ext, DenseEmbedder)
        result = ext.embed(["factory test"])
        assert len(result.embeddings[0]) == 1536


class TestSparseEmbedder:
    """Tests for the BM25-style sparse embedder."""

    def test_returns_dict_vectors(self):
        embedder = SparseEmbedder()
        vecs = embedder.embed(["hello world"])
        assert isinstance(vecs, list)
        assert isinstance(vecs[0], dict)

    def test_reproducibility(self):
        embedder = SparseEmbedder()
        v1 = embedder.embed(["temporal workflow"])
        v2 = embedder.embed(["temporal workflow"])
        assert v1[0] == v2[0]

    def test_different_texts_different_keys(self):
        embedder = SparseEmbedder()
        v1 = embedder.embed(["hello"])
        v2 = embedder.embed(["world"])
        assert v1[0].keys() != v2[0].keys()

    def test_l2_normalised_sparse_values(self):
        embedder = SparseEmbedder()
        vec = embedder.embed(["normalisation verification text here"])[0]
        magnitude = math.sqrt(sum(v**2 for v in vec.values()))
        assert pytest.approx(magnitude, abs=1e-6) == 1.0

    def test_empty_text_returns_empty_dict(self):
        embedder = SparseEmbedder()
        assert embedder.embed([""])[0] == {}

    def test_model_name(self):
        assert SparseEmbedder().model_name == "sparse"

    def test_get_sparse_embedder_factory(self):
        embedder = get_sparse_embedder()
        assert isinstance(embedder, SparseEmbedder)


class TestEmbeddingResult:
    """Tests for the EmbeddingResult dataclass."""

    def test_fields(self):
        result = EmbeddingResult(
            embeddings=[[0.1, 0.2]],
            model="dense",
            dimensions=1536,
            count=1,
        )
        assert result.count == 1
        assert result.model == "dense"
