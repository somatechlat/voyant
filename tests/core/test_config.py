import os

import pytest

from apps.core.config import Settings


def _backup_voyant_env():
    """Snapshot all VOYANT_ prefixed env vars so we can restore them later."""
    return {k: v for k, v in os.environ.items() if k.startswith("VOYANT_")}


def _restore_voyant_env(backup: dict):
    """Remove any VOYANT_ vars added during the test and restore the original set."""
    for k in list(os.environ.keys()):
        if k.startswith("VOYANT_"):
            del os.environ[k]
    os.environ.update(backup)


class TestConfig:
    def test_settings_default_values(self):
        backup = _backup_voyant_env()
        _restore_voyant_env({})
        os.environ["VOYANT_SECRET_KEY"] = (
            "test-key-of-sufficient-length-for-django-validation-1234"
        )
        os.environ["VOYANT_DEBUG"] = "false"
        try:
            settings = Settings()
            assert settings.debug is False
            assert settings.env == "local"
        finally:
            _restore_voyant_env(backup)

    def test_vault_enforcement(self):
        backup = _backup_voyant_env()
        _restore_voyant_env({})
        os.environ["VOYANT_ENV"] = "production"
        os.environ["VOYANT_SECRET_KEY"] = "some-key"
        os.environ["VOYANT_SECRETS_BACKEND"] = "env"
        try:
            from pydantic import ValidationError

            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "SECURITY VIOLATION" in str(exc.value)
        finally:
            _restore_voyant_env(backup)

    def test_trino_url_generation(self):
        backup = _backup_voyant_env()
        _restore_voyant_env({})
        os.environ["VOYANT_TRINO_USER"] = "test-user"
        os.environ["VOYANT_TRINO_HOST"] = "trino-host"
        os.environ["VOYANT_TRINO_PORT"] = "8080"
        os.environ["VOYANT_TRINO_CATALOG"] = "hive"
        os.environ["VOYANT_SECRET_KEY"] = (
            "test-key-of-sufficient-length-for-django-validation-1234"
        )
        try:
            settings = Settings()
            assert settings.trino_user == "test-user"
            assert settings.trino_host == "trino-host"
        finally:
            _restore_voyant_env(backup)
