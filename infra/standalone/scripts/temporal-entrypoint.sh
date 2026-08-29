#!/bin/sh
# Wrapper for Temporal auto-setup that reads POSTGRES_PWD from Docker secret file.
set -e

if [ -n "$POSTGRES_PWD_FILE" ] && [ -r "$POSTGRES_PWD_FILE" ]; then
  export POSTGRES_PWD
  POSTGRES_PWD=$(cat "$POSTGRES_PWD_FILE")
fi

exec /etc/temporal/entrypoint.sh "$@"
