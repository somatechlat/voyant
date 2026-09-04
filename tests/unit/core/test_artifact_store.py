"""
Unit tests for apps.core.lib.artifact_store — Content-addressable artifact store.

Real in-memory store with temp directories. No mocks, no external services.
"""

import gzip
import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from apps.core.lib.artifact_store import (
    ArtifactRef,
    ArtifactStore,
    CompressionType,
    HashAlgorithm,
    StoreConfig,
)


@pytest.fixture
def tmp_base(tmp_path):
    """Provide a temporary base path for the artifact store."""
    return str(tmp_path / "artifacts")


@pytest.fixture
def store(tmp_base):
    """Provide a fresh ArtifactStore with a temp directory."""
    config = StoreConfig(base_path=tmp_base, compression=CompressionType.NONE)
    return ArtifactStore(config)


@pytest.fixture
def gzip_store(tmp_base):
    """Provide a fresh ArtifactStore with gzip compression."""
    config = StoreConfig(base_path=tmp_base, compression=CompressionType.GZIP)
    return ArtifactStore(config)


# =============================================================================
# StoreConfig Tests
# =============================================================================


class TestStoreConfig:
    def test_defaults(self):
        cfg = StoreConfig()
        assert cfg.base_path == "./artifacts"
        assert cfg.hash_algorithm == HashAlgorithm.SHA256
        assert cfg.compression == CompressionType.GZIP
        assert cfg.shard_depth == 2
        assert cfg.shard_width == 2
        assert cfg.enable_dedup is True
        assert cfg.store_metadata is True
        assert cfg.max_artifact_size_mb == 100

    def test_get_storage_path(self):
        cfg = StoreConfig(base_path="/data", shard_depth=2, shard_width=2)
        path = cfg.get_storage_path("abcdef1234567890")
        # First 2 chars: "ab", next 2: "cd"
        assert path == Path("/data") / "ab" / "cd" / "abcdef1234567890"

    def test_get_storage_path_single_shard(self):
        cfg = StoreConfig(base_path="/data", shard_depth=1, shard_width=3)
        path = cfg.get_storage_path("abcdef1234567890")
        assert path == Path("/data") / "abc" / "abcdef1234567890"


# =============================================================================
# ArtifactRef Tests
# =============================================================================


class TestArtifactRef:
    def test_creation(self):
        ref = ArtifactRef(
            hash="sha256:abc123",
            size_bytes=1024,
            artifact_type="profile",
            compression=CompressionType.GZIP,
        )
        assert ref.hash == "sha256:abc123"
        assert ref.size_bytes == 1024
        assert ref.artifact_type == "profile"
        assert ref.compression == CompressionType.GZIP
        # created_at should be auto-set
        assert ref.created_at != ""

    def test_algorithm_property(self):
        ref = ArtifactRef(
            hash="sha256:abc123", size_bytes=0, artifact_type="test",
            compression=CompressionType.NONE,
        )
        assert ref.algorithm == "sha256"

    def test_hash_value_property(self):
        ref = ArtifactRef(
            hash="sha256:abc123", size_bytes=0, artifact_type="test",
            compression=CompressionType.NONE,
        )
        assert ref.hash_value == "abc123"

    def test_hash_value_without_colon(self):
        ref = ArtifactRef(
            hash="abc123", size_bytes=0, artifact_type="test",
            compression=CompressionType.NONE,
        )
        assert ref.hash_value == "abc123"

    def test_to_dict(self):
        ref = ArtifactRef(
            hash="sha256:abc123",
            size_bytes=512,
            artifact_type="chart",
            compression=CompressionType.NONE,
            metadata={"key": "value"},
        )
        d = ref.to_dict()
        assert d["hash"] == "sha256:abc123"
        assert d["size_bytes"] == 512
        assert d["artifact_type"] == "chart"
        assert d["compression"] == "none"
        assert d["metadata"] == {"key": "value"}

    def test_from_dict_roundtrip(self):
        ref = ArtifactRef(
            hash="sha256:abc123",
            size_bytes=512,
            artifact_type="chart",
            compression=CompressionType.GZIP,
            metadata={"key": "value"},
        )
        d = ref.to_dict()
        ref2 = ArtifactRef.from_dict(d)
        assert ref2.hash == ref.hash
        assert ref2.size_bytes == ref.size_bytes
        assert ref2.artifact_type == ref.artifact_type
        assert ref2.compression == ref.compression
        assert ref2.metadata == ref.metadata

    def test_from_dict_defaults(self):
        d = {
            "hash": "sha256:abc",
            "size_bytes": 100,
            "artifact_type": "test",
        }
        ref = ArtifactRef.from_dict(d)
        assert ref.compression == CompressionType.NONE
        # created_at is auto-set by __post_init__ when empty
        assert ref.created_at != ""
        assert ref.metadata == {}


# =============================================================================
# ArtifactStore — Basic Operations
# =============================================================================


class TestArtifactStoreBasic:
    def test_store_and_retrieve(self, store):
        content = b"hello world"
        ref = store.store(content, "test")
        assert ref.size_bytes == len(content)
        assert ref.artifact_type == "test"

        retrieved = store.retrieve(ref.hash)
        assert retrieved == content

    def test_store_with_metadata(self, store):
        ref = store.store(b"data", "profile", metadata={"source": "test"})
        assert ref.metadata == {"source": "test"}

    def test_retrieve_nonexistent(self, store):
        result = store.retrieve("sha256:nonexistent")
        assert result is None

    def test_retrieve_by_hash_only(self, store):
        content = b"test content"
        ref = store.store(content, "test")
        hash_only = ref.hash_value
        retrieved = store.retrieve(hash_only)
        assert retrieved == content

    def test_store_empty_content(self, store):
        ref = store.store(b"", "empty")
        assert ref.size_bytes == 0
        retrieved = store.retrieve(ref.hash)
        assert retrieved == b""

    def test_store_large_content(self, store):
        content = b"x" * (1024 * 1024)  # 1MB
        ref = store.store(content, "large")
        assert ref.size_bytes == 1024 * 1024
        retrieved = store.retrieve(ref.hash)
        assert retrieved == content


# =============================================================================
# ArtifactStore — Hash Algorithms
# =============================================================================


class TestArtifactStoreHashAlgorithms:
    def test_sha256(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, hash_algorithm=HashAlgorithm.SHA256,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        ref = store.store(b"test", "test")
        assert ref.algorithm == "sha256"

    def test_sha512(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, hash_algorithm=HashAlgorithm.SHA512,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        ref = store.store(b"test", "test")
        assert ref.algorithm == "sha512"

    def test_blake2b(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, hash_algorithm=HashAlgorithm.BLAKE2B,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        ref = store.store(b"test", "test")
        assert ref.algorithm == "blake2b"


# =============================================================================
# ArtifactStore — Compression
# =============================================================================


class TestArtifactStoreCompression:
    def test_no_compression(self, store):
        content = b"uncompressed data"
        ref = store.store(content, "test")
        assert ref.compression == CompressionType.NONE
        retrieved = store.retrieve(ref.hash)
        assert retrieved == content

    def test_gzip_compression(self, gzip_store):
        content = b"compressible data " * 100
        ref = gzip_store.store(content, "test")
        assert ref.compression == CompressionType.GZIP
        retrieved = gzip_store.retrieve(ref.hash)
        assert retrieved == content

    def test_gzip_stores_compressed_on_disk(self, gzip_store, tmp_base):
        content = b"compressible data " * 100
        ref = gzip_store.store(content, "test")
        hash_value = ref.hash_value
        storage_path = gzip_store.config.get_storage_path(hash_value)
        content_file = storage_path.with_suffix(".bin")
        raw = content_file.read_bytes()
        # Raw file should be gzip-compressed
        decompressed = gzip.decompress(raw)
        assert decompressed == content


# =============================================================================
# ArtifactStore — Deduplication
# =============================================================================


class TestArtifactStoreDedup:
    def test_dedup_returns_same_ref(self, store):
        content = b"duplicate content"
        ref1 = store.store(content, "test")
        ref2 = store.store(content, "test")
        assert ref1.hash == ref2.hash

    def test_dedup_disabled(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, enable_dedup=False,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        content = b"duplicate content"
        ref1 = store.store(content, "test")
        ref2 = store.store(content, "test")
        # Same hash but store is called twice
        assert ref1.hash == ref2.hash

    def test_different_content_different_hash(self, store):
        ref1 = store.store(b"content A", "test")
        ref2 = store.store(b"content B", "test")
        assert ref1.hash != ref2.hash


# =============================================================================
# ArtifactStore — Verification
# =============================================================================


class TestArtifactStoreVerify:
    def test_verify_valid(self, store):
        content = b"verify me"
        ref = store.store(content, "test")
        assert store.verify(ref.hash) is True

    def test_verify_nonexistent(self, store):
        assert store.verify("sha256:doesnotexist") is False

    def test_verify_corrupted(self, store, tmp_base):
        content = b"corrupt me"
        ref = store.store(content, "test")
        # Corrupt the file on disk
        hash_value = ref.hash_value
        storage_path = store.config.get_storage_path(hash_value)
        content_file = storage_path.with_suffix(".bin")
        content_file.write_bytes(b"corrupted")
        assert store.verify(ref.hash) is False


# =============================================================================
# ArtifactStore — Metadata
# =============================================================================


class TestArtifactStoreMetadata:
    def test_metadata_file_written(self, store, tmp_base):
        content = b"metadata test"
        ref = store.store(content, "test")
        hash_value = ref.hash_value
        storage_path = store.config.get_storage_path(hash_value)
        meta_file = storage_path.with_suffix(".json")
        assert meta_file.exists()
        with open(meta_file) as f:
            meta = json.load(f)
        assert meta["hash"] == ref.hash
        assert meta["artifact_type"] == "test"

    def test_metadata_disabled(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, store_metadata=False,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        ref = store.store(b"data", "test")
        hash_value = ref.hash_value
        storage_path = store.config.get_storage_path(hash_value)
        meta_file = storage_path.with_suffix(".json")
        assert not meta_file.exists()


# =============================================================================
# ArtifactStore — get_ref
# =============================================================================


class TestArtifactStoreGetRef:
    def test_get_ref_by_full_hash(self, store):
        ref = store.store(b"data", "test")
        found = store.get_ref(ref.hash)
        assert found is not None
        assert found.hash == ref.hash

    def test_get_ref_by_hash_only(self, store):
        ref = store.store(b"data", "test")
        found = store.get_ref(ref.hash_value)
        assert found is not None
        assert found.hash == ref.hash

    def test_get_ref_from_disk(self, store, tmp_base):
        ref = store.store(b"data", "test")
        # Clear in-memory cache
        store._refs.clear()
        found = store.get_ref(ref.hash_value)
        assert found is not None
        assert found.hash == ref.hash

    def test_get_ref_nonexistent(self, store):
        assert store.get_ref("sha256:nonexistent") is None


# =============================================================================
# ArtifactStore — Delete
# =============================================================================


class TestArtifactStoreDelete:
    def test_delete_existing(self, store):
        ref = store.store(b"delete me", "test")
        assert store.delete(ref.hash) is True
        assert store.retrieve(ref.hash) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("sha256:nonexistent") is False

    def test_delete_removes_files(self, store, tmp_base):
        ref = store.store(b"delete me", "test")
        hash_value = ref.hash_value
        storage_path = store.config.get_storage_path(hash_value)
        assert storage_path.with_suffix(".bin").exists()
        store.delete(ref.hash)
        assert not storage_path.with_suffix(".bin").exists()


# =============================================================================
# ArtifactStore — List & Stats
# =============================================================================


class TestArtifactStoreListAndStats:
    def test_list_artifacts(self, store):
        store.store(b"a", "profile")
        store.store(b"b", "chart")
        store.store(b"c", "profile")
        all_refs = store.list_artifacts()
        assert len(all_refs) == 3

    def test_list_artifacts_by_type(self, store):
        store.store(b"a", "profile")
        store.store(b"b", "chart")
        store.store(b"c", "profile")
        profiles = store.list_artifacts(artifact_type="profile")
        assert len(profiles) == 2
        assert all(r.artifact_type == "profile" for r in profiles)

    def test_list_artifacts_with_limit(self, store):
        for i in range(10):
            store.store(f"content {i}".encode(), "test")
        limited = store.list_artifacts(limit=3)
        assert len(limited) == 3

    def test_get_stats(self, store):
        store.store(b"a" * 100, "profile")
        store.store(b"b" * 200, "chart")
        stats = store.get_stats()
        assert stats["total_artifacts"] == 2
        assert stats["total_size_bytes"] == 300
        assert stats["by_type"]["profile"] == 1
        assert stats["by_type"]["chart"] == 1
        assert stats["dedup_enabled"] is True


# =============================================================================
# ArtifactStore — Garbage Collection
# =============================================================================


class TestArtifactStoreGC:
    def test_gc_no_keep_set(self, store):
        store.store(b"data", "test")
        assert store.gc() == 0

    def test_gc_keeps_specified(self, store):
        ref1 = store.store(b"keep", "test")
        ref2 = store.store(b"remove", "test")
        removed = store.gc(keep_hashes={ref1.hash})
        assert removed == 1
        assert store.retrieve(ref1.hash) is not None
        assert store.retrieve(ref2.hash) is None

    def test_gc_keeps_by_hash_only(self, store):
        ref1 = store.store(b"keep", "test")
        ref2 = store.store(b"remove", "test")
        removed = store.gc(keep_hashes={ref1.hash_value})
        assert removed == 1
        assert store.retrieve(ref1.hash) is not None


# =============================================================================
# ArtifactStore — Size Limit
# =============================================================================


class TestArtifactStoreSizeLimit:
    def test_exceeds_size_limit(self, tmp_base):
        config = StoreConfig(base_path=tmp_base, max_artifact_size_mb=1)
        store = ArtifactStore(config)
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(ValueError, match="exceeds limit"):
            store.store(content, "test")

    def test_within_size_limit(self, tmp_base):
        config = StoreConfig(
            base_path=tmp_base, max_artifact_size_mb=1,
            compression=CompressionType.NONE,
        )
        store = ArtifactStore(config)
        content = b"x" * (512 * 1024)  # 512KB
        ref = store.store(content, "test")
        assert ref.size_bytes == len(content)
