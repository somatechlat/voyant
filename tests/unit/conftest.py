"""
Unit test conftest — NO DB, NO services, NO I/O.

All fixtures here are pure-logic only. If a fixture needs a database
or external service, it belongs in integration/ or e2e/ conftest.
"""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
