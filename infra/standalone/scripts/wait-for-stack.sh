#!/usr/bin/env bash
set -euo pipefail

ENDPOINT=${1:-${VOYANT_READY_ENDPOINT:-}}
if [[ -z "${ENDPOINT}" ]]; then
  echo "VOYANT_READY_ENDPOINT is required" >&2
  exit 1
fi
TIMEOUT=${TIMEOUT:-120}
INTERVAL=3

start=$(date +%s)
>&2 echo "Waiting for readiness at $ENDPOINT (timeout ${TIMEOUT}s)..."
while true; do
  if curl -fsS "$ENDPOINT" | grep -q '"status"'; then
    status=$(curl -fsS "$ENDPOINT" | sed -n 's/.*"status" *: *"\([^"]*\)".*/\1/p')
    if [[ "$status" == "ready" || "$status" == "degraded" ]]; then
      echo "Stack ready (status=$status)"
      exit 0
    fi
  fi
  now=$(date +%s)
  if (( now - start > TIMEOUT )); then
    echo "Timed out waiting for readiness" >&2
    exit 1
  fi
  sleep $INTERVAL
done
