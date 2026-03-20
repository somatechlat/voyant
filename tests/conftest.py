# tests/conftest.py
import os

import pytest

# 1. Force environment variables for host-to-Docker integration
# These MUST be set before any Django or apps imports
os.environ["VOYANT_ENV"] = "local"
os.environ["VOYANT_DATABASE_URL"] = "postgresql://voyant:voyant@localhost:45432/voyant"
os.environ["VOYANT_REDIS_URL"] = "redis://:voyant@localhost:45379/0"
os.environ["VOYANT_KEYCLOAK_URL"] = "http://localhost:45180"
os.environ["VOYANT_KEYCLOAK_REALM"] = "voyant"
os.environ["KEYCLOAK_REALM"] = "voyant"
os.environ["VOYANT_KEYCLOAK_CLIENT_ID"] = "voyant-api"
os.environ["KEYCLOAK_CLIENT_ID"] = "voyant-api"
os.environ["VOYANT_TEMPORAL_HOST"] = "localhost:45233"
os.environ["TEMPORAL_HOST"] = "localhost:45233"
os.environ["VOYANT_SPICEDB_ENDPOINT"] = "localhost:50051"
os.environ["VOYANT_SPICEDB_GRPC_PRESHARED_KEY"] = (
    "frvZpc09vF46n4E0ypHnSUlGohuMma9OPQBX7yagcnbbeqqzQopFxauff2aHt7IR"
)
os.environ["VOYANT_SECRET_KEY"] = (
    "test-secret-key-for-testing-only-min-50-chars-long-django-security"
)
os.environ["VOYANT_ALLOWED_HOSTS"] = (
    '["*"]'  # Must be valid JSON for Pydantic list[str]
)
os.environ["VOYANT_DEBUG"] = "false"
os.environ["VOYANT_SECURITY_ENABLED"] = "false"

# 2. Reset Settings and Service Singletons
from apps.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

# Warm up settings and force overrides if necessary
# If Pydantic still fails to parse from env, we set manually
# Re-fetch to get fresh instance with env vars
s = get_settings()
s.database_url = os.environ["VOYANT_DATABASE_URL"]
s.redis_url = os.environ["VOYANT_REDIS_URL"]
s.keycloak_url = os.environ["VOYANT_KEYCLOAK_URL"]
s.keycloak_realm = os.environ.get("VOYANT_KEYCLOAK_REALM", "voyant")
s.temporal_host = os.environ["VOYANT_TEMPORAL_HOST"]
s.spicedb_endpoint = os.environ["VOYANT_SPICEDB_ENDPOINT"]
s.spicedb_grpc_preshared_key = os.environ["VOYANT_SPICEDB_GRPC_PRESHARED_KEY"]
s.allowed_hosts = ["*"]

import apps.core.security.auth  # noqa: E402

apps.core.security.auth._auth = None

import apps.core.security.policy  # noqa: E402

# policy module has a singleton instance 'spicedb'
from apps.core.security.policy import SpiceDBClient  # noqa: E402

apps.core.security.policy.spicedb = SpiceDBClient()

import apps.core.lib.temporal_client  # noqa: E402

apps.core.lib.temporal_client._client = None


@pytest.fixture(autouse=True)
def force_settings_isolation(settings):
    """
    Ensure each test gets isolated settings and respects our overrides.
    """
    settings.SECRET_KEY = os.environ["VOYANT_SECRET_KEY"]
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "voyant",
            "USER": "voyant",
            "PASSWORD": "voyant",
            "HOST": "localhost",
            "PORT": "45432",
        }
    }
