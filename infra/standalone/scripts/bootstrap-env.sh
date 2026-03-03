#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STANDALONE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${1:-$STANDALONE_DIR/.env}"
TEMPLATE_FILE="$STANDALONE_DIR/.env.example"

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$TEMPLATE_FILE" "$ENV_FILE"
fi

set_kv() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(printf '%s' "$value" | sed 's/[&|]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

get_kv() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- || true
}

is_placeholder() {
  local value="$1"
  [[ -z "$value" || "$value" == replace-* ]]
}

rand_hex() {
  openssl rand -hex 24
}

rand_b64_urlsafe() {
  openssl rand -base64 48 | tr -d '\n=' | tr '/+' 'ab' | cut -c1-64
}

ensure_secret() {
  local key="$1"
  local generator="$2"
  local current
  current="$(get_kv "$key")"
  if is_placeholder "$current"; then
    set_kv "$key" "$($generator)"
  fi
}

ensure_secret "VOYANT_SECRET_KEY" rand_b64_urlsafe
ensure_secret "SECRET_KEY" rand_b64_urlsafe
set_kv "COMPOSE_PROJECT_NAME" "voyant_cluster"
ensure_secret "POSTGRES_PASSWORD" rand_b64_urlsafe
ensure_secret "REDIS_PASSWORD" rand_b64_urlsafe
ensure_secret "MINIO_ACCESS_KEY" rand_hex
ensure_secret "MINIO_SECRET_KEY" rand_b64_urlsafe
ensure_secret "MINIO_ROOT_USER" rand_hex
ensure_secret "MINIO_ROOT_PASSWORD" rand_b64_urlsafe
ensure_secret "KEYCLOAK_CLIENT_SECRET" rand_b64_urlsafe
ensure_secret "KEYCLOAK_ADMIN" rand_hex
ensure_secret "KEYCLOAK_ADMIN_PASSWORD" rand_b64_urlsafe
ensure_secret "DATAHUB_SECRET" rand_b64_urlsafe
ensure_secret "LAGO_API_KEY" rand_b64_urlsafe
ensure_secret "LAGO_SECRET_KEY" rand_b64_urlsafe
ensure_secret "LAGO_ENCRYPTION_KEY" rand_b64_urlsafe
ensure_secret "SPICEDB_GRPC_PRESHARED_KEY" rand_b64_urlsafe

LAGO_RSA_PRIVATE_KEY_CURRENT="$(get_kv "LAGO_RSA_PRIVATE_KEY")"
if is_placeholder "$LAGO_RSA_PRIVATE_KEY_CURRENT"; then
  LAGO_RSA_PRIVATE_KEY_NEW="$(openssl genrsa 2048 2>/dev/null | base64 | tr -d '\n')"
  set_kv "LAGO_RSA_PRIVATE_KEY" "$LAGO_RSA_PRIVATE_KEY_NEW"
fi

POSTGRES_PASSWORD="$(get_kv "POSTGRES_PASSWORD")"
REDIS_PASSWORD="$(get_kv "REDIS_PASSWORD")"
VOYANT_SECRET_KEY="$(get_kv "VOYANT_SECRET_KEY")"
SECRET_KEY="$(get_kv "SECRET_KEY")"

if is_placeholder "$SECRET_KEY" && ! is_placeholder "$VOYANT_SECRET_KEY"; then
  set_kv "SECRET_KEY" "$VOYANT_SECRET_KEY"
elif is_placeholder "$VOYANT_SECRET_KEY" && ! is_placeholder "$SECRET_KEY"; then
  set_kv "VOYANT_SECRET_KEY" "$SECRET_KEY"
else
  set_kv "SECRET_KEY" "$VOYANT_SECRET_KEY"
fi

set_kv "DATABASE_URL" "postgresql://voyant:${POSTGRES_PASSWORD}@voyant_postgres:5432/voyant"
set_kv "REDIS_URL" "redis://:${REDIS_PASSWORD}@voyant_redis:6379/0"
set_kv "KC_DB_PASSWORD" "$POSTGRES_PASSWORD"
set_kv "DATAHUB_DATABASE_PASSWORD" "$POSTGRES_PASSWORD"
set_kv "LAGO_DATABASE_URL" "postgresql://voyant:${POSTGRES_PASSWORD}@voyant-postgres:5432/lago"
set_kv "LAGO_REDIS_URL" "redis://:${REDIS_PASSWORD}@voyant_redis:6379/2"

rm -f "${ENV_FILE}.bak"
echo "Bootstrapped secrets in $ENV_FILE"
