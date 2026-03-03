#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STANDALONE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$STANDALONE_DIR/docker-compose.yml"
ENV_FILE="$STANDALONE_DIR/.env"

"$SCRIPT_DIR/bootstrap-env.sh" "$ENV_FILE"

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(grep -E '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" | head -n1 | cut -d'=' -f2-)}"
PROJECT_NAME="${PROJECT_NAME:-voyant_cluster}"

docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans

docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

services=(
  voyant_api
  voyant_worker
  voyant_postgres
  voyant_redis
  voyant_kafka
  voyant_minio
  voyant_keycloak
  voyant_lago_api
  voyant_lago_worker
  voyant_temporal
  voyant_temporal_ui
  voyant_trino
  voyant_vault
  voyant_elasticsearch
)

health_or_running() {
  local name="$1"
  local state
  state="$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "missing")"
  if [[ "$state" != "running" ]]; then
    return 1
  fi
  return 0
}

deadline=$((SECONDS + 420))
while (( SECONDS < deadline )); do
  all_ok=1
  for s in "${services[@]}"; do
    if ! health_or_running "$s"; then
      all_ok=0
      break
    fi
  done
  if (( all_ok == 1 )); then
    break
  fi
  sleep 5
done

if (( all_ok != 1 )); then
  echo "Cluster did not reach running state in time" >&2
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
  exit 1
fi

# Basic smoke tests with retries
smoke_deadline=$((SECONDS + 300))
while (( SECONDS < smoke_deadline )); do
  if curl -fsS http://localhost:45000/healthz >/dev/null \
    && curl -fsS http://localhost:45900/minio/health/live >/dev/null \
    && curl -fsS http://localhost:45180/health/ready >/dev/null \
    && curl -fsS http://localhost:45080/v1/info >/dev/null; then
    break
  fi
  sleep 5
done

if (( SECONDS >= smoke_deadline )); then
  echo "Cluster running but smoke checks did not pass in time" >&2
  exit 1
fi

# Restart-count check for critical services
for s in voyant_api voyant_worker voyant_lago_api voyant_lago_worker voyant_keycloak voyant_minio; do
  rc="$(docker inspect --format '{{.RestartCount}}' "$s")"
  if [[ "$rc" != "0" ]]; then
    echo "Service $s has restart count $rc" >&2
    exit 1
  fi
done

echo "Cluster startup verified: healthy and resilient"
