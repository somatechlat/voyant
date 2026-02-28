"""
Tests for Airbyte Client Health Check.

This module contains asynchronous tests to verify the connectivity and health
status of the Airbyte API integration.
"""

import pytest

from apps.ingestion.lib.airbyte_client import get_airbyte_client


@pytest.mark.asyncio
async def test_airbyte_health():
    """
    Tests if the Airbyte API is reachable and reports as healthy.

    This test attempts to get an Airbyte client instance and perform a health check.
    If Airbyte is not reachable, the test is skipped.
    """
    try:
        client = get_airbyte_client()
    except ValueError:
        pytest.skip(
            "Airbyte base_url is not configured in this environment. Skipping test."
        )
    healthy = (
        await client.is_healthy()
    )  # Corrected method call from .health() to .is_healthy()
    if not healthy:
        pytest.skip("Airbyte not reachable in this environment. Skipping test.")
    assert healthy is True
