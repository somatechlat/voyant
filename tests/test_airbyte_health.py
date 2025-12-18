import pytest
from voyant.ingestion.airbyte_client import get_airbyte_client

@pytest.mark.asyncio
async def test_airbyte_health():
    client = get_airbyte_client()
    healthy = await client.health()
    if not healthy:
        pytest.skip("Airbyte not reachable in this environment")
    assert healthy is True
