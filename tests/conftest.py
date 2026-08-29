# tests/conftest.py
import os
from pathlib import Path

# DJANGO_SETTINGS_MODULE must be set before any Django or ninja imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

import pytest

# ---------------------------------------------------------------------------
# Read secrets from infra/standalone/secrets/ files (NO hardcoded credentials)
# ---------------------------------------------------------------------------
_secrets_dir = Path(__file__).resolve().parent.parent / "infra" / "standalone" / "secrets"


def _read_secret(name: str, default: str = "") -> str:
    """Read a secret from the secrets directory."""
    p = _secrets_dir / name
    if p.is_file():
        try:
            return p.read_text().strip() or default
        except OSError:
            pass
    return default


def _rewrite_host(url: str, host: str = "localhost") -> str:
    """Rewrite Docker-internal hostnames to localhost for host-side tests."""
    import re
    return re.sub(r"voyant_\w+", host, url)


# 1. Force environment variables for host-to-Docker integration
# These MUST be set before any Django or apps imports
os.environ["VOYANT_ENV"] = "local"

_HostSide = _secrets_dir.is_dir()

_pg_password = _read_secret("postgres_password", "")
if _HostSide:
    os.environ["VOYANT_DATABASE_URL"] = f"postgresql://voyant:{_pg_password}@localhost:45432/voyant"
    _redis_password = _read_secret("redis_password", "")
    os.environ["VOYANT_REDIS_URL"] = f"redis://:{_redis_password}@localhost:45379/0"
    os.environ["VOYANT_KEYCLOAK_URL"] = "http://localhost:45180"
    os.environ["VOYANT_TEMPORAL_HOST"] = "localhost:45233"
    os.environ["TEMPORAL_HOST"] = "localhost:45233"
    os.environ["VOYANT_SPICEDB_ENDPOINT"] = "localhost:50051"
else:
    # Running inside a Docker container — use Docker service hostnames.
    # VOYANT_DATABASE_URL and VOYANT_REDIS_URL are already set by
    # _resolve_docker_secrets() in config.py (reads /run/secrets/*_FILE).
    # Only set if not already present (Docker secrets take precedence).
    os.environ.setdefault("VOYANT_KEYCLOAK_URL", "http://voyant_keycloak:8080")
    os.environ.setdefault("VOYANT_TEMPORAL_HOST", "voyant_temporal:7233")
    os.environ.setdefault("TEMPORAL_HOST", "voyant_temporal:7233")
    os.environ.setdefault("VOYANT_SPICEDB_ENDPOINT", "voyant_spicedb:50051")

os.environ["VOYANT_KEYCLOAK_REALM"] = "voyant"
os.environ["KEYCLOAK_REALM"] = "voyant"
os.environ["VOYANT_KEYCLOAK_CLIENT_ID"] = "voyant-api"
os.environ["KEYCLOAK_CLIENT_ID"] = "voyant-api"
if _HostSide:
    _spicedb_key = _read_secret("spicedb_grpc_preshared_key")
    os.environ.setdefault("VOYANT_SPICEDB_GRPC_PRESHARED_KEY", _spicedb_key)
else:
    # In Docker, read from the mounted secret file directly.
    _docker_secret = Path("/run/secrets/spicedb_grpc_preshared_key")
    if _docker_secret.is_file():
        os.environ.setdefault("VOYANT_SPICEDB_GRPC_PRESHARED_KEY", _docker_secret.read_text().strip())

_secret_key = _read_secret("secret_key")
if not _secret_key:
    _secret_key = "test-secret-key-for-testing-only-min-50-chars-long-django-security"
os.environ["VOYANT_SECRET_KEY"] = _secret_key
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
# In Docker, secrets resolve to DATABASE_URL (not VOYANT_DATABASE_URL)
s.database_url = os.environ.get("VOYANT_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
s.redis_url = os.environ.get("VOYANT_REDIS_URL") or os.environ.get("REDIS_URL", "")
s.keycloak_url = os.environ.get("VOYANT_KEYCLOAK_URL") or os.environ.get("KEYCLOAK_URL", "")
s.keycloak_realm = os.environ.get("VOYANT_KEYCLOAK_REALM", "voyant")
s.temporal_host = os.environ["VOYANT_TEMPORAL_HOST"]
s.spicedb_endpoint = os.environ["VOYANT_SPICEDB_ENDPOINT"]
s.spicedb_grpc_preshared_key = os.environ.get("VOYANT_SPICEDB_GRPC_PRESHARED_KEY", "")
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

    # Parse DATABASE_URL to extract connection details (password from secrets)
    _database_url = os.environ.get("VOYANT_DATABASE_URL", "")
    if _database_url and "://" in _database_url:
        import urllib.parse
        _parsed = urllib.parse.urlparse(_database_url)
        _db_host = _parsed.hostname or ("localhost" if _HostSide else "voyant_postgres")
        _db_port = str(_parsed.port or (45432 if _HostSide else 5432))
        _db_password = _parsed.password or ""
        _db_name = (_parsed.path or "/voyant").lstrip("/") or "voyant"
        _db_user = _parsed.username or "voyant"
    else:
        _db_host = "localhost" if _HostSide else "voyant_postgres"
        _db_port = "45432" if _HostSide else "5432"
        _db_password = _pg_password or ""
        _db_name = "voyant"
        _db_user = "voyant"
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_name,
            "USER": _db_user,
            "PASSWORD": _db_password,
            "HOST": _db_host,
            "PORT": _db_port,
        }
    }
