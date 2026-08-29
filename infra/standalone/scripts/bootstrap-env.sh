#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Bootstrap Secrets for Voyant Standalone Stack
# =============================================================================
# Generates secrets in ./secrets/ directory ONLY.
# Secrets NEVER go in .env files. They are:
#   1. Mounted as Docker secrets at /run/secrets/ for infrastructure containers
#   2. Seeded into Vault for application containers at runtime
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STANDALONE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR="$STANDALONE_DIR/secrets"

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required" >&2
  exit 1
fi

mkdir -p "$SECRETS_DIR"

rand_hex() {
  openssl rand -hex 24
}

rand_b64_urlsafe() {
  openssl rand -base64 48 | tr -d '\n=' | tr '/+' 'ab' | cut -c1-64
}

write_secret() {
  local name="$1"
  local value="$2"
  local file="$SECRETS_DIR/$name"
  # Only write if file doesn't exist or is empty
  if [ ! -s "$file" ]; then
    printf '%s' "$value" > "$file"
    chmod 600 "$file"
    echo "Generated: $name"
  else
    echo "Exists:    $name"
  fi
}

# --- Generate secrets ---
SECRET_KEY="$(rand_b64_urlsafe)"
POSTGRES_PASSWORD="$(rand_b64_urlsafe)"
REDIS_PASSWORD="$(rand_b64_urlsafe)"
MINIO_ACCESS_KEY="$(rand_hex)"
MINIO_SECRET_KEY="$(rand_b64_urlsafe)"
MINIO_ROOT_USER="$(rand_hex)"
MINIO_ROOT_PASSWORD="$(rand_b64_urlsafe)"
KEYCLOAK_CLIENT_SECRET="$(rand_b64_urlsafe)"
KEYCLOAK_ADMIN_PASSWORD="$(rand_b64_urlsafe)"
SPICEDB_GRPC_PRESHARED_KEY="$(rand_b64_urlsafe)"
DATAHUB_SECRET="$(rand_b64_urlsafe)"

# Vault root token (matches VAULT_DEV_ROOT_TOKEN_ID in docker-compose.yml)
# Dev-mode only — production uses auto-unseal + AppRole/Kubernetes auth.
VAULT_TOKEN="voyant-root-token"

# --- Write secret files ---
write_secret "secret_key" "$SECRET_KEY"
write_secret "postgres_password" "$POSTGRES_PASSWORD"
write_secret "redis_password" "$REDIS_PASSWORD"
write_secret "minio_access_key" "$MINIO_ACCESS_KEY"
write_secret "minio_secret_key" "$MINIO_SECRET_KEY"
write_secret "minio_root_user" "$MINIO_ROOT_USER"
write_secret "minio_root_password" "$MINIO_ROOT_PASSWORD"
write_secret "keycloak_client_secret" "$KEYCLOAK_CLIENT_SECRET"
write_secret "keycloak_admin_password" "$KEYCLOAK_ADMIN_PASSWORD"
write_secret "spicedb_grpc_preshared_key" "$SPICEDB_GRPC_PRESHARED_KEY"
write_secret "datahub_secret" "$DATAHUB_SECRET"
write_secret "vault_token" "$VAULT_TOKEN"
write_secret "mcp_api_token" ""

# --- Write composite connection URLs ---
write_secret "database_url" "postgresql://voyant:${POSTGRES_PASSWORD}@voyant_postgres:5432/voyant"
write_secret "redis_url" "redis://:${REDIS_PASSWORD}@voyant_redis:6379/0"

echo ""
echo "Secrets generated in $SECRETS_DIR"
echo "NO secrets written to .env files."
echo ""
echo "Next steps:"
echo "  docker compose up -d"
echo "  docker compose exec voyant_vault /scripts/seed-vault.sh  # seed Vault with secrets"
