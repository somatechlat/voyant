"""
Unit tests for apps.core.lib.secrets — Secrets backend abstraction.

Real in-memory and env backends. No mocks, no external services.
"""

import os

import pytest

from apps.core.lib.secrets import (
    EnvSecretsBackend,
    InMemorySecretsBackend,
    K8sSecretsBackend,
    SecretMetadata,
)

# =============================================================================
# SecretMetadata Tests
# =============================================================================


class TestSecretMetadata:
    def test_creation(self):
        meta = SecretMetadata(
            key="api_key",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert meta.key == "api_key"
        assert meta.version == 1
        assert meta.expires_at is None
        assert meta.tags == {}

    def test_to_dict(self):
        meta = SecretMetadata(
            key="k", created_at="t1", updated_at="t2",
            expires_at="t3", version=2, tags={"env": "prod"},
        )
        d = meta.to_dict()
        assert d["key"] == "k"
        assert d["version"] == 2
        assert d["expires_at"] == "t3"
        assert d["tags"] == {"env": "prod"}


# =============================================================================
# InMemorySecretsBackend Tests
# =============================================================================


class TestInMemorySecretsBackend:
    @pytest.fixture
    def backend(self):
        return InMemorySecretsBackend()

    @pytest.mark.asyncio
    async def test_provider_name(self, backend):
        assert backend.provider_name == "memory"

    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        await backend.set("api_key", "secret123")
        value = await backend.get("api_key")
        assert value == "secret123"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        value = await backend.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        await backend.set("key", "value")
        result = await backend.delete("key")
        assert result is True
        assert await backend.get("key") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, backend):
        result = await backend.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_keys(self, backend):
        await backend.set("key1", "v1")
        await backend.set("key2", "v2")
        keys = await backend.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, backend):
        keys = await backend.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    async def test_version_increments(self, backend):
        await backend.set("key", "v1")
        await backend.set("key", "v2")
        meta = await backend.get_metadata("key")
        assert meta is not None
        assert meta.version == 2

    @pytest.mark.asyncio
    async def test_created_at_preserved(self, backend):
        await backend.set("key", "v1")
        meta1 = await backend.get_metadata("key")
        created = meta1.created_at

        await backend.set("key", "v2")
        meta2 = await backend.get_metadata("key")
        assert meta2.created_at == created
        assert meta2.updated_at != created

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, backend):
        meta = await backend.get_metadata("nonexistent")
        assert meta is None

    @pytest.mark.asyncio
    async def test_set_with_expiration(self, backend):
        await backend.set("key", "value", expires_in=3600)
        meta = await backend.get_metadata("key")
        assert meta.expires_at is not None

    @pytest.mark.asyncio
    async def test_expiration_is_set(self, backend):
        # Set with a short expiry
        await backend.set("key", "value", expires_in=60)
        meta = await backend.get_metadata("key")
        assert meta.expires_at is not None
        assert meta.expires_at.endswith("Z")


# =============================================================================
# EnvSecretsBackend Tests
# =============================================================================


class TestEnvSecretsBackend:
    @pytest.fixture
    def backend(self):
        return EnvSecretsBackend()

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean up test env vars."""
        keys_to_clean = [k for k in os.environ if k.startswith("TEST_SECRET")]
        for k in keys_to_clean:
            del os.environ[k]
        yield
        keys_to_clean = [k for k in os.environ if k.startswith("TEST_SECRET")]
        for k in keys_to_clean:
            del os.environ[k]

    @pytest.mark.asyncio
    async def test_provider_name(self, backend):
        assert backend.provider_name == "env"

    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        await backend.set("test_secret_key", "value123")
        result = await backend.get("test_secret_key")
        assert result == "value123"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        result = await backend.get("test_secret_nonexistent_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        await backend.set("test_secret_del", "val")
        result = await backend.delete("test_secret_del")
        assert result is True
        assert await backend.get("test_secret_del") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, backend):
        result = await backend.delete("test_secret_noexist_abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_key_normalization(self, backend):
        """Keys are uppercased and special chars replaced with underscores."""
        await backend.set("test/my-key", "val")
        assert os.environ.get("TEST_MY_KEY") == "val"

    @pytest.mark.asyncio
    async def test_get_metadata(self, backend):
        await backend.set("test_secret_meta", "val")
        meta = await backend.get_metadata("test_secret_meta")
        assert meta is not None
        assert meta.key == "test_secret_meta"
        assert meta.version == 1

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, backend):
        meta = await backend.get_metadata("test_secret_noexist_xyz")
        assert meta is None


# =============================================================================
# K8sSecretsBackend Tests
# =============================================================================


class TestK8sSecretsBackend:
    @pytest.fixture
    def backend(self, tmp_path):
        return K8sSecretsBackend(root=str(tmp_path / "secrets"))

    @pytest.mark.asyncio
    async def test_provider_name(self, backend):
        assert backend.provider_name == "k8s"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, backend):
        result = await backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_is_readonly(self, backend):
        result = await backend.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_is_readonly(self, backend):
        result = await backend.delete("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_keys_empty_dir(self, backend):
        keys = await backend.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    async def test_get_from_file(self, backend, tmp_path):
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir(parents=True, exist_ok=True)
        (secret_dir / "my_secret").write_text("secret_value\n")
        result = await backend.get("my_secret")
        assert result == "secret_value"

    @pytest.mark.asyncio
    async def test_list_keys_with_files(self, backend, tmp_path):
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir(parents=True, exist_ok=True)
        (secret_dir / "key1").write_text("v1")
        (secret_dir / "key2").write_text("v2")
        keys = await backend.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_get_metadata(self, backend, tmp_path):
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir(parents=True, exist_ok=True)
        (secret_dir / "my_secret").write_text("value")
        meta = await backend.get_metadata("my_secret")
        assert meta is not None
        assert meta.key == "my_secret"

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, backend):
        meta = await backend.get_metadata("nonexistent")
        assert meta is None
