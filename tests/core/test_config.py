import os
from unittest.mock import patch

import pytest

from apps.core.config import Settings


class TestConfig:
    def test_settings_default_values(self):
        # Ensure we can instantiate Settings without mandatory env vars in test mode
        with patch.dict(
            os.environ,
            {
                "VOYANT_SECRET_KEY": "test-key-of-sufficient-length-for-django-validation-1234"
            },
        ):
            settings = Settings()
            assert settings.debug is False
            assert settings.env == "local"

    def test_vault_enforcement(self):
        # Settings should allow env-based secrets ONLY in local env
        # non-local environments MUST use vault or similar
        with patch.dict(
            os.environ,
            {
                "VOYANT_ENV": "production",
                "VOYANT_SECRET_KEY": "some-key",
                "VOYANT_SECRETS_BACKEND": "env",
            },
        ):
            from pydantic import ValidationError

            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "SECURITY VIOLATION" in str(exc.value)

    def test_trino_url_generation(self):
        with patch.dict(
            os.environ,
            {
                "VOYANT_TRINO_USER": "test-user",
                "VOYANT_TRINO_HOST": "trino-host",
                "VOYANT_TRINO_PORT": "8080",
                "VOYANT_TRINO_CATALOG": "hive",
            },
        ):
            settings = Settings()
            assert settings.trino_user == "test-user"
            assert settings.trino_host == "trino-host"
            # Verify any computed properties if they exist
