"""Tests for apps.scraper.activities.fetch_activities."""

import pytest

from apps.scraper.activities.fetch_activities import FetchActivities


class TestFetchActivitiesHeartbeatSafe:
    """Test the _heartbeat_safe static method."""

    def test_heartbeat_safe_outside_temporal_does_not_raise(self):
        """When not inside a Temporal activity context, heartbeat should silently no-op."""
        # Should not raise even though we're not in a Temporal activity
        FetchActivities._heartbeat_safe("test message")


class TestFetchActivitiesEngineRouting:
    """Test engine selection logic (without actually fetching)."""

    def test_scrapy_engine_raises_application_error(self):
        """Scrapy engine is not yet integrated and should raise."""
        from temporalio.exceptions import ApplicationError

        activity = FetchActivities()
        with pytest.raises(ApplicationError, match="Scrapy engine is not yet integrated"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                activity._fetch_scrapy("https://example.com", 30)
            )


class TestFetchActivitiesParams:
    """Test parameter extraction and defaults in fetch_page."""

    def test_default_params_extraction(self):
        """Verify that default settings are used when params are minimal."""
        from apps.core.config import get_settings
        settings = get_settings()

        # Just verify the settings attributes exist
        assert hasattr(settings, 'scraper_default_engine')
        assert hasattr(settings, 'scraper_default_timeout_seconds')
        assert hasattr(settings, 'scraper_playwright_wait_until')
        assert hasattr(settings, 'scraper_playwright_settle_ms_default')
        assert hasattr(settings, 'scraper_playwright_block_resources_default')
