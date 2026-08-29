"""
Integration test conftest — real DB, real services.

Provides fixtures for tests that need PostgreSQL, Redis, Temporal, etc.
Tests skip gracefully when services are unavailable.
"""

import os

import pytest


def _service_available(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP service is reachable."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


@pytest.fixture(scope="session")
def postgres_available():
    """Check if PostgreSQL is reachable."""
    host = os.environ.get("VOYANT_DB_HOST", "localhost")
    port = int(os.environ.get("VOYANT_DB_PORT", "45432"))
    return _service_available(host, port)


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is reachable."""
    host = os.environ.get("VOYANT_REDIS_HOST", "localhost")
    port = int(os.environ.get("VOYANT_REDIS_PORT", "45379"))
    return _service_available(host, port)


@pytest.fixture(scope="session")
def temporal_available():
    """Check if Temporal is reachable."""
    host = os.environ.get("VOYANT_TEMPORAL_HOST", "localhost")
    port = int(os.environ.get("VOYANT_TEMPORAL_PORT", "45233"))
    return _service_available(host, port)


@pytest.fixture(scope="session")
def milvus_available():
    """Check if Milvus is reachable."""
    host = os.environ.get("VOYANT_MILVUS_HOST", "localhost")
    port = int(os.environ.get("VOYANT_MILVUS_PORT", "45195"))
    return _service_available(host, port)


@pytest.fixture
def skip_without_postgres(postgres_available):
    if not postgres_available:
        pytest.skip("PostgreSQL not available")


@pytest.fixture
def skip_without_redis(redis_available):
    if not redis_available:
        pytest.skip("Redis not available")
