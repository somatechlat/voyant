"""
E2E test conftest — full HTTP stack, Django Ninja test client.

Provides authenticated and unauthenticated test clients for
hitting real API endpoints through the full middleware stack.
"""

import os

import pytest


@pytest.fixture
def api_client(client, settings):
    """Django test client with auth bypassed."""
    settings.VOYANT_SECURITY_ENABLED = False
    return client


@pytest.fixture
def auth_headers():
    """Headers that bypass auth in test mode."""
    return {
        "HTTP_AUTHORIZATION": "Bearer test-token",
        "CONTENT_TYPE": "application/json",
    }
