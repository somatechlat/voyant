import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.core.lib.secrets import get_secret, get_secrets_backend, set_secret

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_vault")

async def verify_vault():
    logger.info("Starting Vault verification...")

    # Ensure backend is Vault
    backend = get_secrets_backend()
    if backend.provider_name != "vault":
        logger.error(f"Current backend is '{backend.provider_name}', expected 'vault'")
        logger.info("Please set VOYANT_SECRETS_BACKEND=vault")
        sys.exit(1)

    logger.info(f"Connected to backend: {backend.provider_name}")

    test_key = "test_verification_secret"
    test_value = "s3cr3t_v4lu3_123"

    # 1. Set Secret
    logger.info(f"Setting secret '{test_key}'...")
    success = await set_secret(test_key, test_value)
    if not success:
        logger.error("Failed to set secret")
        sys.exit(1)
    logger.info("Secret set successfully.")

    # 2. Get Secret
    logger.info(f"Retrieving secret '{test_key}'...")
    value = await get_secret(test_key)

    if value == test_value:
        logger.info("✅ SUCCESS: Secret retrieved and matches original value.")
    else:
        logger.error(f"❌ FAILURE: Retrieved value '{value}' does not match expected '{test_value}'")
        sys.exit(1)

    # 3. Clean up (Optional, maybe keep for audit?)
    # await backend.delete(test_key)

if __name__ == "__main__":
    try:
        asyncio.run(verify_vault())
    except Exception as e:
        logger.exception(f"Verification failed: {e}")
        sys.exit(1)
