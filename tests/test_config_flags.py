"""
Tests for Feature Flag Configuration.

This module contains tests that verify the application's ability to correctly
load and apply feature flag settings from environment variables, ensuring
conditional functionalities behave as expected based on configuration.
"""

from apps.core.config import get_settings


def test_feature_flags_env(monkeypatch):
    """
    Verifies that feature flags are correctly set via environment variables.

    This test uses `monkeypatch` to set specific environment variables
    (`VOYANT_ENABLE_QUALITY`, `VOYANT_ENABLE_CHARTS`, `VOYANT_ENABLE_NARRATIVE`)
    and then asserts that `get_settings()` reflects these values after
    clearing the settings cache.
    """
    # Required list fields must be valid JSON for pydantic-settings parsing.
    monkeypatch.setenv("VOYANT_ALLOWED_HOSTS", '["*","localhost","testserver"]')
    monkeypatch.setenv("VOYANT_ENV", "local")
    monkeypatch.setenv("VOYANT_SECRETS_BACKEND", "env")
    monkeypatch.setenv(
        "VOYANT_SECRET_KEY",
        "test-secret-key-for-feature-flag-tests-minimum-50-chars-long",
    )

    # Set environment variables for feature flags.
    monkeypatch.setenv("VOYANT_ENABLE_QUALITY", "0")
    monkeypatch.setenv("VOYANT_ENABLE_CHARTS", "0")
    monkeypatch.setenv("VOYANT_ENABLE_NARRATIVE", "1")

    # Clear the cached settings to force a reload from environment variables.
    from apps.core.config import get_settings as gs

    gs.cache_clear()  # type: ignore

    # Retrieve settings and assert that feature flags are correctly applied.
    s = get_settings()
    assert s.enable_quality is False
    assert s.enable_charts is False
    assert s.enable_narrative is True

    # Restore cache after test
    gs.cache_clear()  # type: ignore
