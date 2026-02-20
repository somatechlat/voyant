
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.security.policy import spicedb
from authzed.api.v1 import WriteSchemaRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deploy_schema")

async def deploy_schema():
    schema_path = Path("voyant/security/schema.zed")
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)

    schema_content = schema_path.read_text()
    logger.info(f"Read schema from {schema_path} ({len(schema_content)} bytes)")

    try:
        logger.info("Writing schema to SpiceDB...")
        # Note: The client in policy.py might need a small tweak to expose the grpc client
        # or we use the underlying client directly.
        # spicedb.client is the property that returns the authzed Client

        client = spicedb.client
        client.schema_service.WriteSchema(
             WriteSchemaRequest(schema=schema_content)
        )
        logger.info("✅ Schema deployed successfully.")

    except Exception as e:
        logger.error(f"❌ Failed to deploy schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(deploy_schema())
