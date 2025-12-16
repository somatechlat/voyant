import os
from temporalio.client import Client

_client = None

async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        host = os.getenv("TEMPORAL_HOST", "temporal:7233")
        _client = await Client.connect(host)
    return _client
