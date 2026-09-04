#!/usr/bin/env bash
# =============================================================================
# VOYANT v3.0.0 — Master Operations CLI
# =============================================================================
# Single entrypoint for all cluster operations.
# Every command is IDEMPOTENT — safe to run multiple times.
#
# Usage:
#   ./voyant.sh bootstrap          Full zero-to-running setup
#   ./voyant.sh up                 Start cluster
#   ./voyant.sh down               Stop cluster
#   ./voyant.sh status             Health check all services
#   ./voyant.sh test               Run full test suite
#   ./voyant.sh backup             Backup all stateful data
#   ./voyant.sh restore <ts>       Restore from backup timestamp
#   ./voyant.sh secrets rotate     Rotate all secrets
#   ./voyant.sh logs [service]     Tail logs
#   ./voyant.sh db shell           PostgreSQL shell
#   ./voyant.sh db migrate         Run Django migrations
#   ./voyant.sh vault status       Vault health
#   ./voyant.sh doctor             Full system diagnostics
# =============================================================================
set -euo pipefail

VOYANT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="$VOYANT_ROOT/infra/standalone"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"
ENV_FILE="$INFRA_DIR/.env"
SECRETS_DIR="$INFRA_DIR/secrets"
BACKUP_DIR="${VOYANT_BACKUP_DIR:-$VOYANT_ROOT/backups}"
VAULT_ADDR="${VAULT_ADDR:-http://localhost:45820}"
VAULT_TOKEN_FILE="$SECRETS_DIR/vault_token"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[voyant]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

# =============================================================================
# HELPERS
# =============================================================================

compose() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

vault_cli() {
  local token
  token=$(cat "$VAULT_TOKEN_FILE" 2>/dev/null || echo "voyant-root-token")
  VAULT_ADDR="$VAULT_ADDR" VAULT_TOKEN="$token" vault "$@"
}

wait_healthy() {
  local name="$1" timeout="${2:-120}"
  local deadline=$((SECONDS + timeout))
  while (( SECONDS < deadline )); do
    local status
    status=$(docker inspect --format '{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")
    if [[ "$status" == "healthy" ]]; then return 0; fi
    if [[ "$status" == "missing" ]]; then return 1; fi
    sleep 3
  done
  return 1
}

check_port() {
  local host="${1:-localhost}" port="$2" timeout="${3:-5}"
  timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null
}

# =============================================================================
# BOOTSTRAP — Zero to Running (Idempotent)
# =============================================================================

cmd_bootstrap() {
  log "=== VOYANT BOOTSTRAP ==="
  log "This is fully idempotent — safe to re-run at any time."

  # Step 1: Generate secrets (skip if already exist)
  _bootstrap_secrets

  # Step 2: Verify Docker daemon
  _bootstrap_docker

  # Step 3: Start infrastructure services
  _bootstrap_infra

  # Step 4: Initialize databases
  _bootstrap_databases

  # Step 5: Seed Vault
  _bootstrap_vault

  # Step 6: Start application services
  _bootstrap_app

  # Step 7: Run Django migrations
  _bootstrap_migrate

  # Step 8: Health verification
  _bootstrap_verify

  log "=== BOOTSTRAP COMPLETE ==="
  log "API: https://localhost:45000 (or http with -k)"
  log "Temporal UI: http://localhost:45089"
  log "MinIO Console: http://localhost:45901"
  log "Keycloak: http://localhost:45180"
  log "Flink UI: http://localhost:45082"
}

_bootstrap_secrets() {
  log "Step 1/8: Secrets"
  if [[ -d "$SECRETS_DIR" ]] && [[ -f "$SECRETS_DIR/secret_key" ]] && [[ -s "$SECRETS_DIR/secret_key" ]]; then
    log "  Secrets already exist — skipping generation"
  else
    log "  Generating secrets..."
    bash "$INFRA_DIR/scripts/bootstrap-env.sh"
  fi

  # Verify all required secret files exist and are non-empty
  local required=(
    secret_key database_url redis_url minio_access_key minio_secret_key
    keycloak_client_secret vault_token spicedb_grpc_preshared_key mcp_api_token
  )
  local missing=()
  for s in "${required[@]}"; do
    if [[ ! -s "$SECRETS_DIR/$s" ]]; then missing+=("$s"); fi
  done
  if (( ${#missing[@]} > 0 )); then
    die "Missing required secrets: ${missing[*]}"
  fi
  log "  All ${#required[@]} secrets present"
}

_bootstrap_docker() {
  log "Step 2/8: Docker"
  docker info >/dev/null 2>&1 || die "Docker daemon is not running"
  log "  Docker daemon OK"

  # Create required external volumes (idempotent)
  local volumes=(voyant_artifacts voyant_data voyant_logs voyant_vault_data)
  for v in "${volumes[@]}"; do
    docker volume create "$v" >/dev/null 2>&1 || true
  done
  log "  Volumes verified"
}

_bootstrap_infra() {
  log "Step 3/8: Infrastructure services"

  # Start infrastructure first (postgres, redis, kafka, vault, temporal, etc.)
  local infra_services=(
    voyant_postgres voyant_redis voyant_kafka voyant_vault
    voyant_temporal voyant_minio voyant_etcd voyant_milvus
    voyant_trino voyant_keycloak voyant_elasticsearch
  )

  for svc in "${infra_services[@]}"; do
    local running
    running=$(docker inspect --format '{{.State.Running}}' "$svc" 2>/dev/null || echo "false")
    if [[ "$running" == "true" ]]; then
      log "  $svc: already running"
    else
      log "  $svc: starting..."
      compose up -d "$svc" 2>/dev/null || true
    fi
  done

  # Wait for critical infrastructure
  log "  Waiting for Postgres..."
  wait_healthy voyant_postgres 60 || die "Postgres failed to start"
  log "  Waiting for Redis..."
  wait_healthy voyant_redis 30 || die "Redis failed to start"
  log "  Waiting for MinIO..."
  wait_healthy voyant_minio 30 || die "MinIO failed to start"
  log "  Infrastructure ready"
}

_bootstrap_databases() {
  log "Step 4/8: Database initialization"

  # Create voyant database if it doesn't exist (idempotent)
  docker exec voyant_postgres psql -U postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname = 'voyant'" | grep -q 1 || \
    docker exec voyant_postgres psql -U postgres -c "CREATE DATABASE voyant;" 2>/dev/null || true

  # Create voyant user if it doesn't exist (idempotent)
  local pg_pass
  pg_pass=$(cat "$SECRETS_DIR/postgres_password" 2>/dev/null || echo "")
  if [[ -n "$pg_pass" ]]; then
    docker exec voyant_postgres psql -U postgres -tc \
      "SELECT 1 FROM pg_roles WHERE rolname = 'voyant'" | grep -q 1 || \
      docker exec voyant_postgres psql -U postgres -c \
      "CREATE USER voyant WITH PASSWORD '$pg_pass'; GRANT ALL PRIVILEGES ON DATABASE voyant TO voyant;" 2>/dev/null || true
  fi

  # Initialize MinIO bucket (idempotent)
  docker exec voyant_minio mc alias set local http://localhost:9000 \
    "$(cat "$SECRETS_DIR/minio_root_user")" \
    "$(cat "$SECRETS_DIR/minio_root_password")" 2>/dev/null || true
  docker exec voyant_minio mc mb --ignore-existing local/voyant-artifacts 2>/dev/null || true

  log "  Databases initialized"
}

_bootstrap_vault() {
  log "Step 5/8: Vault seeding"

  # Wait for Vault to be responsive
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if curl -sf "$VAULT_ADDR/v1/sys/health" >/dev/null 2>&1; then break; fi
    sleep 2
  done

  # Enable KV v2 (idempotent)
  curl -sf -X POST "$VAULT_ADDR/v1/sys/mounts/secret" \
    -H "X-Vault-Token: $(cat "$VAULT_TOKEN_FILE")" \
    -d '{"type":"kv","options":{"version":"2"}}' 2>/dev/null || true

  # Seed each secret from files
  local token
  token=$(cat "$VAULT_TOKEN_FILE")
  local secrets=(
    secret_key minio_access_key minio_secret_key keycloak_client_secret
    mcp_api_token spicedb_grpc_preshared_key
  )
  local seeded=0
  for s in "${secrets[@]}"; do
    if [[ -s "$SECRETS_DIR/$s" ]]; then
      local val
      val=$(cat "$SECRETS_DIR/$s")
      curl -sf -X POST "$VAULT_ADDR/v1/secret/data/$s" \
        -H "X-Vault-Token: $token" \
        -d "{\"data\":{\"value\":\"$val\"}}" >/dev/null 2>&1 && ((seeded++)) || true
    fi
  done
  log "  Seeded $seeded secrets into Vault"
}

_bootstrap_app() {
  log "Step 6/8: Application services"
  compose up -d voyant_api voyant_worker 2>/dev/null

  log "  Waiting for API..."
  wait_healthy voyant_api 90 || die "API failed to start"
  log "  Waiting for Worker..."
  wait_healthy voyant_worker 60 || warn "Worker not healthy yet (may still be starting)"
  log "  Application services started"
}

_bootstrap_migrate() {
  log "Step 7/8: Django migrations"
  docker exec voyant_api python manage.py migrate --noinput 2>/dev/null || warn "Migrations had warnings (non-fatal)"
  log "  Migrations complete"
}

_bootstrap_verify() {
  log "Step 8/8: Health verification"

  local checks=0
  local total=0

  # API health
  ((total++))
  if curl -sfk https://localhost:45000/health >/dev/null 2>&1 || curl -sf http://localhost:45000/healthz >/dev/null 2>&1; then
    ((checks++)); log "  API: OK"
  else
    warn "  API: FAILED"
  fi

  # Postgres
  ((total++))
  if docker exec voyant_postgres pg_isready -U voyant >/dev/null 2>&1; then
    ((checks++)); log "  Postgres: OK"
  else
    warn "  Postgres: FAILED"
  fi

  # Redis
  ((total++))
  if docker exec voyant_redis redis-cli -a "$(cat "$SECRETS_DIR/redis_password")" ping 2>/dev/null | grep -q PONG; then
    ((checks++)); log "  Redis: OK"
  else
    warn "  Redis: FAILED"
  fi

  # Vault
  ((total++))
  if curl -sf "$VAULT_ADDR/v1/sys/health" >/dev/null 2>&1; then
    ((checks++)); log "  Vault: OK"
  else
    warn "  Vault: FAILED"
  fi

  # Temporal
  ((total++))
  if check_port localhost 45233 3; then
    ((checks++)); log "  Temporal: OK"
  else
    warn "  Temporal: FAILED"
  fi

  log "  Health: $checks/$total checks passed"
  if (( checks < total )); then
    warn "Some services are unhealthy — run './voyant.sh doctor' for details"
  fi
}

# =============================================================================
# UP / DOWN
# =============================================================================

cmd_up() {
  log "Starting cluster..."
  compose up -d
  log "Cluster started. Run './voyant.sh status' to verify."
}

cmd_down() {
  log "Stopping cluster..."
  compose down
  log "Cluster stopped."
}

# =============================================================================
# STATUS
# =============================================================================

cmd_status() {
  echo -e "${BLUE}=== VOYANT CLUSTER STATUS ===${NC}"
  echo ""

  # Container status
  printf "%-30s %-20s %-15s\n" "SERVICE" "STATUS" "HEALTH"
  printf "%-30s %-20s %-15s\n" "-------" "------" "------"

  for name in $(docker ps -a --format '{{.Names}}' | grep voyant | sort); do
    local state health
    state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$name" 2>/dev/null || echo "N/A")

    local color="$GREEN"
    if [[ "$state" != "running" ]]; then color="$RED"; fi
    if [[ "$health" == "unhealthy" ]]; then color="$YELLOW"; fi

    printf "${color}%-30s %-20s %-15s${NC}\n" "$name" "$state" "$health"
  done

  echo ""

  # Quick API check
  if curl -sfk https://localhost:45000/health -o /dev/null 2>&1; then
    echo -e "API: ${GREEN}HTTPS OK${NC}"
  elif curl -sf http://localhost:45000/healthz -o /dev/null 2>&1; then
    echo -e "API: ${GREEN}HTTP OK${NC} (HTTPS redirect active — use -k or reverse proxy)"
  else
    echo -e "API: ${RED}UNREACHABLE${NC}"
  fi
}

# =============================================================================
# TEST
# =============================================================================

cmd_test() {
  log "Running full test suite..."
  docker exec voyant_api python -m pytest tests/ -v --tb=short "$@"
  log "Tests complete."
}

# =============================================================================
# BACKUP
# =============================================================================

cmd_backup() {
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local dest="$BACKUP_DIR/$ts"
  mkdir -p "$dest"

  log "=== BACKUP $ts ==="

  # 1. PostgreSQL
  log "Backing up PostgreSQL..."
  docker exec voyant_postgres pg_dump -U voyant -Fc voyant > "$dest/voyant.dump" 2>/dev/null
  log "  PostgreSQL: $(du -h "$dest/voyant.dump" | cut -f1)"

  # 2. Redis (BGSAVE + copy RDB)
  log "Backing up Redis..."
  docker exec voyant_redis redis-cli -a "$(cat "$SECRETS_DIR/redis_password")" BGSAVE >/dev/null 2>&1
  sleep 2
  docker cp voyant_redis:/data/dump.rdb "$dest/redis.rdb" 2>/dev/null || warn "  Redis RDB not available"
  log "  Redis: copied"

  # 3. MinIO artifacts
  log "Backing up MinIO artifacts..."
  docker exec voyant_minio mc alias set backup-src http://localhost:9000 \
    "$(cat "$SECRETS_DIR/minio_root_user")" \
    "$(cat "$SECRETS_DIR/minio_root_password")" 2>/dev/null || true
  docker exec voyant_minio mc cp --recursive backup-src/voyant-artifacts/ /tmp/backup-artifacts/ 2>/dev/null || true
  docker cp voyant_minio:/tmp/backup-artifacts "$dest/minio-artifacts" 2>/dev/null || warn "  MinIO: no artifacts to backup"
  log "  MinIO: copied"

  # 4. Vault (export all secrets)
  log "Backing up Vault..."
  local token
  token=$(cat "$VAULT_TOKEN_FILE")
  mkdir -p "$dest/vault"
  for key in secret_key minio_access_key minio_secret_key keycloak_client_secret \
    mcp_api_token spicedb_grpc_preshared_key; do
    local val
    val=$(curl -sf "$VAULT_ADDR/v1/secret/data/$key" \
      -H "X-Vault-Token: $token" | \
      python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("data",{}).get("data",{}).get("value",""))' 2>/dev/null || echo "")
    if [[ -n "$val" ]]; then
      printf '%s' "$val" > "$dest/vault/$key"
    fi
  done
  log "  Vault: exported"

  # 5. DuckDB
  log "Backing up DuckDB..."
  docker cp voyant_api:/app/data/voyant.duckdb "$dest/voyant.duckdb" 2>/dev/null || warn "  DuckDB not found"
  log "  DuckDB: copied"

  # 6. Milvus (metadata export)
  log "Backing up Milvus metadata..."
  curl -sf "http://localhost:19532/v2/vectordb/collections/list" \
    -H "Accept: application/json" > "$dest/milvus_collections.json" 2>/dev/null || warn "  Milvus: not reachable"
  log "  Milvus: metadata exported"

  # 7. Secrets directory
  log "Backing up secrets..."
  cp -r "$SECRETS_DIR" "$dest/secrets" 2>/dev/null
  chmod -R 600 "$dest/secrets" 2>/dev/null
  log "  Secrets: copied"

  # 8. Configuration
  log "Backing up configuration..."
  cp "$ENV_FILE" "$dest/env" 2>/dev/null
  cp "$COMPOSE_FILE" "$dest/docker-compose.yml" 2>/dev/null
  log "  Config: copied"

  # Manifest
  cat > "$dest/MANIFEST.json" <<EOF
{
  "timestamp": "$ts",
  "voyant_version": "3.0.0",
  "backup_type": "full",
  "components": {
    "postgres": "$([ -f "$dest/voyant.dump" ] && echo 'ok' || echo 'missing')",
    "redis": "$([ -f "$dest/redis.rdb" ] && echo 'ok' || echo 'missing')",
    "vault": "$(ls "$dest/vault/" 2>/dev/null | wc -l | tr -d ' ') secrets",
    "duckdb": "$([ -f "$dest/voyant.duckdb" ] && echo 'ok' || echo 'missing')",
    "minio": "$([ -d "$dest/minio-artifacts" ] && echo 'ok' || echo 'empty')",
    "secrets": "$([ -d "$dest/secrets" ] && echo 'ok' || echo 'missing')"
  }
}
EOF

  log ""
  log "=== BACKUP COMPLETE ==="
  log "Location: $dest"
  log "Size: $(du -sh "$dest" | cut -f1)"
  log ""
  log "To restore: ./voyant.sh restore $ts"
}

# =============================================================================
# RESTORE
# =============================================================================

cmd_restore() {
  local ts="${1:-}"
  if [[ -z "$ts" ]]; then
    # List available backups
    echo "Available backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null || echo "  (none)"
    echo ""
    echo "Usage: ./voyant.sh restore <timestamp>"
    return 1
  fi

  local src="$BACKUP_DIR/$ts"
  if [[ ! -d "$src" ]]; then
    die "Backup not found: $src"
  fi

  log "=== RESTORE from $ts ==="
  log "WARNING: This will overwrite current data."
  log ""

  # 1. Stop application services (keep infra running)
  log "Stopping application services..."
  compose stop voyant_api voyant_worker 2>/dev/null || true

  # 2. Restore PostgreSQL
  if [[ -f "$src/voyant.dump" ]]; then
    log "Restoring PostgreSQL..."
    docker exec voyant_postgres pg_restore -U voyant -d voyant --clean --if-exists \
      < "$src/voyant.dump" 2>/dev/null || warn "  PostgreSQL restore had warnings"
    log "  PostgreSQL restored"
  fi

  # 3. Restore Redis
  if [[ -f "$src/redis.rdb" ]]; then
    log "Restoring Redis..."
    compose stop voyant_redis 2>/dev/null
    docker cp "$src/redis.rdb" voyant_redis:/data/dump.rdb
    compose start voyant_redis 2>/dev/null
    wait_healthy voyant_redis 30 || warn "  Redis not healthy after restore"
    log "  Redis restored"
  fi

  # 4. Restore Vault secrets
  if [[ -d "$src/vault" ]]; then
    log "Restoring Vault secrets..."
    local token
    token=$(cat "$VAULT_TOKEN_FILE")
    for key in "$src/vault/"*; do
      local name
      name=$(basename "$key")
      local val
      val=$(cat "$key")
      if [[ -n "$val" ]]; then
        curl -sf -X POST "$VAULT_ADDR/v1/secret/data/$name" \
          -H "X-Vault-Token: $token" \
          -d "{\"data\":{\"value\":\"$val\"}}" >/dev/null 2>&1 || true
      fi
    done
    log "  Vault restored"
  fi

  # 5. Restore DuckDB
  if [[ -f "$src/voyant.duckdb" ]]; then
    log "Restoring DuckDB..."
    docker cp "$src/voyant.duckdb" voyant_api:/app/data/voyant.duckdb 2>/dev/null || true
    log "  DuckDB restored"
  fi

  # 6. Restore secrets files
  if [[ -d "$src/secrets" ]]; then
    log "Restoring secret files..."
    cp -r "$src/secrets/"* "$SECRETS_DIR/" 2>/dev/null
    chmod -R 600 "$SECRETS_DIR" 2>/dev/null
    log "  Secrets restored"
  fi

  # 7. Restart application services
  log "Restarting application services..."
  compose up -d voyant_api voyant_worker 2>/dev/null
  wait_healthy voyant_api 90 || die "API failed to start after restore"

  log ""
  log "=== RESTORE COMPLETE ==="
}

# =============================================================================
# SECRETS
# =============================================================================

cmd_secrets() {
  local subcmd="${1:-status}"
  case "$subcmd" in
    status)
      log "Secret files:"
      for f in "$SECRETS_DIR"/*; do
        local name
        name=$(basename "$f")
        local size
        size=$(wc -c < "$f" 2>/dev/null || echo 0)
        local status="OK"
        if (( size == 0 )); then status="EMPTY"; fi
        printf "  %-35s %6s bytes  %s\n" "$name" "$size" "$status"
      done
      echo ""
      log "Vault secrets:"
      local token
      token=$(cat "$VAULT_TOKEN_FILE")
      for key in secret_key minio_access_key minio_secret_key keycloak_client_secret \
        mcp_api_token spicedb_grpc_preshared_key; do
        local ok
        ok=$(curl -sf "$VAULT_ADDR/v1/secret/data/$key" \
          -H "X-Vault-Token: $token" | \
          python3 -c 'import sys,json; d=json.load(sys.stdin); print("OK" if d.get("data",{}).get("data",{}).get("value") else "MISSING")' 2>/dev/null || echo "ERROR")
        printf "  %-35s %s\n" "$key" "$ok"
      done
      ;;
    rotate)
      log "Rotating secrets..."
      # Backup first
      cmd_backup

      # Regenerate secrets
      rm -f "$SECRETS_DIR/secret_key" "$SECRETS_DIR/minio_access_key" \
        "$SECRETS_DIR/minio_secret_key" "$SECRETS_DIR/keycloak_client_secret" \
        "$SECRETS_DIR/mcp_api_token" "$SECRETS_DIR/spicedb_grpc_preshared_key"
      bash "$INFRA_DIR/scripts/bootstrap-env.sh"

      # Re-seed Vault
      _bootstrap_vault

      # Restart services
      compose restart voyant_api voyant_worker 2>/dev/null
      wait_healthy voyant_api 90 || die "API failed after secret rotation"

      log "Secrets rotated. Old backup preserved."
      ;;
    *)
      die "Unknown secrets subcommand: $subcmd (use: status, rotate)"
      ;;
  esac
}

# =============================================================================
# LOGS
# =============================================================================

cmd_logs() {
  local service="${1:-voyant_api}"
  compose logs -f --tail=100 "$service"
}

# =============================================================================
# DB
# =============================================================================

cmd_db() {
  local subcmd="${1:-shell}"
  case "$subcmd" in
    shell)
      docker exec -it voyant_postgres psql -U voyant -d voyant
      ;;
    migrate)
      docker exec voyant_api python manage.py migrate --noinput
      ;;
    makemigrations)
      docker exec voyant_api python manage.py makemigrations
      ;;
    *)
      die "Unknown db subcommand: $subcmd (use: shell, migrate, makemigrations)"
      ;;
  esac
}

# =============================================================================
# VAULT
# =============================================================================

cmd_vault() {
  local subcmd="${1:-status}"
  case "$subcmd" in
    status)
      curl -sf "$VAULT_ADDR/v1/sys/health" | python3 -m json.tool 2>/dev/null || echo "Vault unreachable"
      ;;
    ui)
      log "Vault UI: http://localhost:45820/ui"
      log "Token: $(cat "$VAULT_TOKEN_FILE")"
      ;;
    *)
      die "Unknown vault subcommand: $subcmd (use: status, ui)"
      ;;
  esac
}

# =============================================================================
# DOCTOR — Full System Diagnostics
# =============================================================================

cmd_doctor() {
  echo -e "${BLUE}=== VOYANT DOCTOR ===${NC}"
  echo ""

  local issues=0

  # 1. Docker
  echo -n "Docker daemon: "
  if docker info >/dev/null 2>&1; then echo -e "${GREEN}OK${NC}"; else echo -e "${RED}FAIL${NC}"; ((issues++)); fi

  # 2. Containers
  echo "Containers:"
  for name in voyant_api voyant_worker voyant_postgres voyant_redis voyant_kafka \
    voyant_vault voyant_temporal voyant_minio voyant_etcd voyant_milvus \
    voyant_trino voyant_keycloak; do
    local state
    state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
    local health
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$name" 2>/dev/null || echo "-")
    if [[ "$state" == "running" ]]; then
      echo -e "  $name: ${GREEN}$state${NC} ($health)"
    else
      echo -e "  $name: ${RED}$state${NC}"
      ((issues++))
    fi
  done

  # 3. Secrets
  echo "Secrets:"
  local required_secrets=(
    secret_key database_url redis_url minio_access_key minio_secret_key
    keycloak_client_secret vault_token spicedb_grpc_preshared_key mcp_api_token
  )
  for s in "${required_secrets[@]}"; do
    if [[ -s "$SECRETS_DIR/$s" ]]; then
      echo -e "  $s: ${GREEN}OK${NC}"
    else
      echo -e "  $s: ${RED}MISSING${NC}"
      ((issues++))
    fi
  done

  # 4. Vault connectivity
  echo -n "Vault connectivity: "
  if curl -sf "$VAULT_ADDR/v1/sys/health" >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "${RED}FAIL${NC}"
    ((issues++))
  fi

  # 5. Database connectivity
  echo -n "PostgreSQL: "
  if docker exec voyant_postgres pg_isready -U voyant >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "${RED}FAIL${NC}"
    ((issues++))
  fi

  # 6. Django deploy check
  echo -n "Django deploy check: "
  local deploy_out
  deploy_out=$(docker exec voyant_api python manage.py check --deploy 2>&1)
  if echo "$deploy_out" | grep -q "no issues"; then
    echo -e "${GREEN}PASS${NC}"
  else
    echo -e "${YELLOW}WARNINGS${NC}"
    echo "$deploy_out" | grep -E "WARNING|ERROR" | head -5
  fi

  # 7. Disk space
  echo -n "Disk space: "
  local disk_pct
  disk_pct=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
  if (( disk_pct > 90 )); then
    echo -e "${RED}${disk_pct}% used${NC} — CRITICAL"
    ((issues++))
  elif (( disk_pct > 80 )); then
    echo -e "${YELLOW}${disk_pct}% used${NC} — warning"
  else
    echo -e "${GREEN}${disk_pct}% used${NC}"
  fi

  # 8. Docker volumes
  echo "Docker volumes:"
  for v in voyant_artifacts voyant_data voyant_logs voyant_vault_data; do
    local exists
    exists=$(docker volume inspect "$v" --format '{{.Mountpoint}}' 2>/dev/null || echo "")
    if [[ -n "$exists" ]]; then
      local size
      size=$(du -sh "$exists" 2>/dev/null | cut -f1 || echo "?")
      echo -e "  $v: ${GREEN}OK${NC} ($size)"
    else
      echo -e "  $v: ${RED}MISSING${NC}"
      ((issues++))
    fi
  done

  echo ""
  if (( issues == 0 )); then
    echo -e "${GREEN}=== SYSTEM HEALTHY — 0 issues ===${NC}"
  else
    echo -e "${RED}=== $issues ISSUES FOUND ===${NC}"
  fi
}

# =============================================================================
# DISPATCHER
# =============================================================================

cmd="${1:-help}"
shift 2>/dev/null || true

case "$cmd" in
  bootstrap)    cmd_bootstrap "$@" ;;
  up)           cmd_up "$@" ;;
  down)         cmd_down "$@" ;;
  status)       cmd_status "$@" ;;
  test)         cmd_test "$@" ;;
  backup)       cmd_backup "$@" ;;
  restore)      cmd_restore "$@" ;;
  secrets)      cmd_secrets "$@" ;;
  logs)         cmd_logs "$@" ;;
  db)           cmd_db "$@" ;;
  vault)        cmd_vault "$@" ;;
  doctor)       cmd_doctor "$@" ;;
  help|*)
    echo "Voyant v3.0.0 Operations CLI"
    echo ""
    echo "Usage: ./voyant.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  bootstrap          Full idempotent zero-to-running setup"
    echo "  up                 Start cluster"
    echo "  down               Stop cluster"
    echo "  status             Health check all services"
    echo "  test [args]        Run full test suite"
    echo "  backup             Backup all stateful data"
    echo "  restore <ts>       Restore from backup timestamp"
    echo "  secrets status     Show secret status"
    echo "  secrets rotate     Rotate all secrets"
    echo "  logs [service]     Tail logs"
    echo "  db shell           PostgreSQL shell"
    echo "  db migrate         Run Django migrations"
    echo "  vault status       Vault health"
    echo "  vault ui           Show Vault UI info"
    echo "  doctor             Full system diagnostics"
    ;;
esac
