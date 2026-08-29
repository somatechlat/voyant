#!/bin/sh
# =============================================================================
# Seed Vault with Voyant Secrets
# =============================================================================
# Run inside the voyant_vault container:
#   docker compose exec voyant_vault sh /vault/scripts/seed-vault.sh
#
# This script:
#   1. Enables the KV v2 secrets engine at "voyant/" mount point
#   2. Reads secrets from /run/secrets/ files
#   3. Writes them into Vault under the "voyant/" prefix
# =============================================================================

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-voyant-root-token}"
MOUNT_POINT="voyant"

export VAULT_ADDR VAULT_TOKEN

echo "=== Seeding Vault at $VAULT_ADDR ==="
echo "Token: ${VAULT_TOKEN:0:8}..."

# Check Vault status
echo "Checking Vault status..."
vault status || true

# Enable KV v2 secrets engine at voyant/ mount
echo "Enabling KV v2 at secret/$MOUNT_POINT/..."
vault secrets enable -path="$MOUNT_POINT" -version=2 kv 2>/dev/null || echo "Already enabled"

# Read secrets from /run/secrets/ and write to Vault
seed_secret() {
  local name="$1"
  local file="/run/secrets/$name"
  if [ -r "$file" ]; then
    local value
    value=$(cat "$file")
    if [ -n "$value" ]; then
      vault kv put "$MOUNT_POINT/$name" value="$value" 2>/dev/null && \
        echo "  Seeded: $name" || echo "  Failed: $name"
    else
      echo "  Skip (empty): $name"
    fi
  else
    echo "  Skip (not found): $name"
  fi
}

echo ""
echo "Seeding secrets into Vault..."
seed_secret "secret_key"
seed_secret "database_url"
seed_secret "redis_url"
seed_secret "postgres_password"
seed_secret "redis_password"
seed_secret "minio_access_key"
seed_secret "minio_secret_key"
seed_secret "minio_root_user"
seed_secret "minio_root_password"
seed_secret "keycloak_client_secret"
seed_secret "keycloak_admin_password"
seed_secret "spicedb_grpc_preshared_key"
seed_secret "vault_token"
seed_secret "datahub_secret"
seed_secret "mcp_api_token"

echo ""
echo "=== Vault seeding complete ==="
echo ""
echo "Verify with:"
echo "  vault kv list voyant/"
echo "  vault kv get voyant/database_url"
