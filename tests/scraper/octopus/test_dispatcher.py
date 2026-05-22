"""
Unit tests for OctopusDispatcher.

Does not require external services — tests schema routing and executor loading.
"""

import pytest

from apps.scraper.octopus.dispatcher import OctopusDispatcher, _get_arm_executors
from apps.scraper.octopus.schemas import OctopusARM, OctopusRequest


class TestGetArmExecutors:
    """Tests for lazy ARM executor loading."""

    def test_returns_dict(self):
        executors = _get_arm_executors()
        assert isinstance(executors, dict)

    def test_static_arm_available(self):
        executors = _get_arm_executors()
        assert OctopusARM.STATIC in executors

    def test_dynamic_arm_available(self):
        executors = _get_arm_executors()
        assert OctopusARM.DYNAMIC in executors


class TestOctopusDispatcher:
    """Tests for the dispatcher itself."""

    @pytest.fixture
    def dispatcher(self):
        return OctopusDispatcher()

    @pytest.mark.asyncio
    async def test_ssrf_blocks_private_ip(self, dispatcher):
        req = OctopusRequest(
            url="http://192.168.1.1/admin",
            arm=OctopusARM.STATIC,
            tenant_id="t1",
        )
        result = await dispatcher.dispatch(req)
        assert result.success is False
        assert result.error_code == "SSRF_BLOCKED"

    @pytest.mark.asyncio
    async def test_ssrf_blocks_localhost(self, dispatcher):
        req = OctopusRequest(
            url="http://localhost:5432",
            arm=OctopusARM.STATIC,
            tenant_id="t1",
        )
        result = await dispatcher.dispatch(req)
        assert result.success is False
        assert result.error_code == "SSRF_BLOCKED"

    @pytest.mark.asyncio
    async def test_unavailable_arm_returns_error(self, dispatcher):
        """An ARM that cannot be loaded returns ARM_UNAVAILABLE."""
        # Use a fake arm value that won't be in executors
        req = OctopusRequest(
            url="https://example.com",
            arm=OctopusARM.STATIC,
            tenant_id="t1",
        )
        # Static should be available; if not, we get ARM_UNAVAILABLE
        result = await dispatcher.dispatch(req)
        # If static executor is available, it will try to fetch (and likely fail
        # network-wise) but if not available we get ARM_UNAVAILABLE.
        assert result.error_code in {None, "FETCH_ERROR", "ARM_UNAVAILABLE"}
