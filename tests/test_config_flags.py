"""
Tests for Feature Flag Configuration.

This module contains tests that verify the application's ability to correctly
load and apply feature flag settings from environment variables, ensuring
conditional functionalities behave as expected based on configuration.
No mocking — environment variables are manipulated directly and restored.
"""

import os

from apps.core.config import get_settings


def _backup_voyant_env():
    return {k: v for k, v in os.environ.items() if k.startswith("VOYANT_")}


def _restore_env(backup):
    for k in list(os.environ.keys()):
        if k.startswith("VOYANT_"):
            del os.environ[k]
    os.environ.update(backup)


def test_feature_flags_env():
    """
    Verifies that feature flags are correctly set via environment variables.

    Sets specific environment variables directly and asserts that
    get_settings() reflects these values after clearing the settings cache.
    """
    backup = _backup_voyant_env()
    _restore_env({})

    # Required list fields must be valid JSON for pydantic-settings parsing.
    os.environ["VOYANT_ALLOWED_HOSTS"] = '["*","localhost","testserver"]'
    os.environ["VOYANT_ENV"] = "local"
    os.environ["VOYANT_SECRETS_BACKEND"] = "env"
    os.environ[
        "VOYANT_SECRET_KEY"
    ] = "test-secret-key-for-feature-flag-tests-minimum-50-chars-long"

    # Set environment variables for feature flags.
    os.environ["VOYANT_ENABLE_QUALITY"] = "0"
    os.environ["VOYANT_ENABLE_CHARTS"] = "0"
    os.environ["VOYANT_ENABLE_NARRATIVE"] = "1"

    try:
        # Clear the cached settings to force a reload from environment variables.
        from apps.core.config import get_settings as gs

        gs.cache_clear()  # type: ignore

        # Retrieve settings and assert that feature flags are correctly applied.
        s = get_settings()
        assert s.enable_quality is False
        assert s.enable_charts is False
        assert s.enable_narrative is True
    finally:
        # Restore cache and environment after test
        gs.cache_clear()  # type: ignore
        _restore_env(backup)
